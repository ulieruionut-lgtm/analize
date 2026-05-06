# -*- coding: utf-8 -*-
"""
Citește PDF, extrage analize, compară cu ce știe aplicația, corectează și învață.
Utilizare: python verifica_si_invata_pdf.py <cale_pdf>
"""
import os
import sys
from pathlib import Path

# Tesseract pe Windows - setează calea înainte de orice import backend
if sys.platform == "win32":
    for p in [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]:
        if os.path.isfile(p):
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = p
            except Exception:
                pass
            os.environ["PATH"] = os.path.dirname(p) + os.pathsep + os.environ.get("PATH", "")
            break

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main(pdf_path: str):
    from backend.pdf_processor import extract_text_from_pdf
    from backend.parser import parse_full_text
    from backend.normalizer import normalize_rezultate, adauga_alias_nou
    from backend.database import get_cursor, _use_sqlite, _row_get

    def get_id_by_cod(cod):
        with get_cursor(commit=False) as cur:
            ph = "?" if _use_sqlite() else "%s"
            cur.execute(f"SELECT id FROM analiza_standard WHERE cod_standard = {ph}", (cod,))
            r = cur.fetchone()
            return _row_get(r, 0 if _use_sqlite() else "id") if r else None

    path = Path(pdf_path)
    if not path.exists():
        print(f"EROARE: Nu există: {pdf_path}")
        return

    print(f"=== Citire: {path.name} ===\n")
    text, tip, err, colored, extractor = extract_text_from_pdf(str(path))
    if err:
        print(f"Avertisment: {err}\n")

    if len(text) < 80:
        print(f"Text insuficient ({len(text)} caractere). PDF scanat fără OCR sau fișier gol.")
        return

    print(f"Extragere: {extractor} | {len(text)} caractere\n")
    parsed = parse_full_text(text, cnp_optional=True)
    if not parsed or not parsed.rezultate:
        print("Nu s-au extras analize din PDF.")
        return

    rez = normalize_rezultate(parsed.rezultate)
    recunoscute = [r for r in rez if r.analiza_standard_id is not None]
    necunoscute = [r for r in rez if r.analiza_standard_id is None]

    print(f"CNP: {parsed.cnp} | Nume: {parsed.nume} {parsed.prenume or ''}\n")
    print(f"--- ANALIZE EXTASE DIN PDF ({len(rez)} total) ---\n")

    def get_cod(aid):
        if not aid:
            return "?"
        try:
            with get_cursor(commit=False) as cur:
                ph = "?" if _use_sqlite() else "%s"
                cur.execute(f"SELECT cod_standard FROM analiza_standard WHERE id = {ph}", (aid,))
                r = cur.fetchone()
                return (_row_get(r, 0 if _use_sqlite() else "cod_standard") or "?")
        except Exception:
            return "?"

    # Ce am găsit eu (citire) vs ce știe aplicația
    print("RECUNOSCUTE (aplicația le-a mapat):")
    for r in recunoscute:
        cod = get_cod(r.analiza_standard_id)
        print(f"  {r.denumire_raw} = {r.valoare} {r.unitate or ''} -> {cod}")

    print(f"\nNECUNOSCUTE ({len(necunoscute)}) - trebuie învățate:")
    for r in necunoscute:
        print(f"  {r.denumire_raw} = {r.valoare} {r.unitate or ''}")

    if necunoscute:
        print("\n--- ÎNVĂȚARE ---")
        raw_set = {r.denumire_raw for r in necunoscute if r.denumire_raw}
        for r in necunoscute:
            raw = r.denumire_raw
            if not raw or len(raw.strip()) < 2:
                continue
            raw_lo = raw.lower().strip()
            valoare = r.valoare
            unitate = (r.unitate or "").lower()
            cod_posibil = None

            # NU mapa Creatinină serică la URINA - e biochimie
            if "creatinin" in raw_lo and "urinar" in raw_lo:
                cod_posibil = "CREAT_URINA"
            elif "creatinin" in raw_lo and "seric" in raw_lo:
                cod_posibil = "CREATININA"
            # Glucoză cu mg/dL sau mmol/L = GLICEMIE, nu urină
            elif "glucoz" in raw_lo and (unitate in ("mg/dl", "mmol/l", "mg/dll") or (valoare and 50 <= valoare <= 400)):
                cod_posibil = "GLUCOZA_FASTING"
            # Leucocite cu /mm³ sau valoare > 100 = WBC hematologie
            elif "leucocit" in raw_lo and ("/mm" in unitate or "/µl" in unitate or (valoare and valoare > 100)):
                cod_posibil = "WBC"
            # Proteine fără unitate sau cu Negativ/Normal = urină
            elif "proteine" in raw_lo and (not unitate or r.valoare_text):
                cod_posibil = "URINA_SUMAR"
            # Restul parametrilor urină (fără creatinină serică, glucoză glicemie)
            elif any(x in raw_lo for x in ["nitrit", "urobilin", "corpi ceton", "pigmen", "cristal", "epitelial", "epltehale", "tranzmonale", "12:11 alte"]) and "seric" not in raw_lo:
                cod_posibil = "URINA_SUMAR"
            elif any(x in raw_lo for x in ["enterococcus", "streptococcus"]) or ("spp" in raw_lo and "flora" not in raw_lo):
                cod_posibil = "FLORA_URINA"
            elif any(x in raw_lo for x in ["hematocrit", "hct"]) and "mcv" not in raw_lo:
                cod_posibil = "HCT"
            elif any(x in raw_lo for x in ["mcv", "volum eritrocitar"]) or (raw_lo == "hematocrit" and unitate == "fl"):
                cod_posibil = "MCV"
            elif "mchc" in raw_lo or ("concentrat" in raw_lo and "hemoglobin" in raw_lo):
                cod_posibil = "MCHC"
            elif ("mch" in raw_lo or ("hemoglobin" in raw_lo and "medie" in raw_lo)) and "mchc" not in raw_lo:
                cod_posibil = "MCH"
            elif any(x in raw_lo for x in ["rdw", "distribut"]):
                cod_posibil = "RDW"
            elif any(x in raw_lo for x in ["eritrocit", "rbc", "hematii"]):
                cod_posibil = "RBC"
            elif any(x in raw_lo for x in ["trombocit", "plt", "plachet"]):
                cod_posibil = "PLT"
            elif any(x in raw_lo for x in ["pdw", "distribuția plachet"]):
                cod_posibil = "PDW"
            elif any(x in raw_lo for x in ["mpv", "volum plachetar"]):
                cod_posibil = "MPV"
            elif "hemoglobin" in raw_lo and "medie" not in raw_lo:
                cod_posibil = "HB"
            elif "tgp" in raw_lo or "alat" in raw_lo:
                cod_posibil = "ALT"
            elif "tgo" in raw_lo or "asat" in raw_lo:
                cod_posibil = "AST"
            elif "tsh" in raw_lo:
                cod_posibil = "TSH"
            elif "ft4" in raw_lo or "tiroxina liber" in raw_lo:
                cod_posibil = "FT4"
            elif "vitamina b12" in raw_lo or "ciancobalamin" in raw_lo:
                cod_posibil = "VIT_B12"
            elif "fier seric" in raw_lo or "sideremie" in raw_lo:
                cod_posibil = "FIER"
            elif "feritin" in raw_lo:
                cod_posibil = "FERITINA"
            elif "calciu" in raw_lo and ("ionic" in raw_lo or "seric" in raw_lo):
                cod_posibil = "CALCIU"
            elif "magneziu" in raw_lo:
                cod_posibil = "MAGNEZIU"
            elif "fosfataza alcalin" in raw_lo or "fosfat" in raw_lo:
                cod_posibil = "ALP"
            elif "neutrofile" in raw_lo and "%" in unitate:
                cod_posibil = "NEUTROFILE_PCT"
            elif "neutrofile" in raw_lo:
                cod_posibil = "NEUTROFILE_NR"
            elif "limfocite" in raw_lo and "%" in unitate:
                cod_posibil = "LIMFOCITE_PCT"
            elif "limfocite" in raw_lo:
                cod_posibil = "LIMFOCITE_NR"
            elif "monocite" in raw_lo and "%" in unitate:
                cod_posibil = "MONOCITE_PCT"
            elif "monocite" in raw_lo:
                cod_posibil = "MONOCITE_NR"
            elif "eozinofile" in raw_lo and "%" in unitate:
                cod_posibil = "EOZINOFILE_PCT"
            elif "eozinofile" in raw_lo:
                cod_posibil = "EOZINOFILE_NR"
            elif "bazofile" in raw_lo and "%" in unitate:
                cod_posibil = "BAZOFILE_PCT"
            elif "bazofile" in raw_lo:
                cod_posibil = "BAZOFILE_NR"
            # Leucocite în context urină (valoare mică, /µL sediment)
            elif "leucocit" in raw_lo and (not unitate or (valoare and valoare < 100)):
                cod_posibil = "URINA_SUMAR"
            # Galben, Limpede - aspect urină
            elif raw_lo in ("galben", "limpede"):
                cod_posibil = "URINA_SUMAR"

            if cod_posibil:
                aid = get_id_by_cod(cod_posibil)
                if aid:
                    try:
                        adauga_alias_nou(raw.strip(), aid)
                        disp = raw[:55] + "..." if len(raw) > 55 else raw
                        print(f"  + ÎNVĂȚAT: '{disp}' -> {cod_posibil}")
                    except Exception as e:
                        print(f"  ! Eroare '{raw[:30]}': {e}")
            else:
                print(f"  ? Fără asociere automată: '{raw[:60]}'")

    print("\nGata. Reîncarcă aplicația pentru a vedea modificările.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Utilizare: python verifica_si_invata_pdf.py <cale_pdf>")
        sys.exit(1)
    main(sys.argv[1])
