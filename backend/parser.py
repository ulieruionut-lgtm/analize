"""Extragere CNP (cu validare), Nume si rezultate analize din text.
Suporta formatele:
 - Bioclinica: parametru pe o linie, valoare + unitate + (interval) pe linia urmatoare
 - MedLife si formate similare: tot pe o linie - Parametru  Valoare  UM  Min-Max UM
"""
import re
from typing import Optional

from backend.models import PatientParsed, RezultatParsat

CNP_CONTROL = (2, 7, 9, 1, 4, 6, 3, 5, 8, 2, 7, 9)

# Linii care NU sunt parametri medicali
_LINII_EXCLUSE = re.compile(
    r"^(Buletin|CNP|ADRESA|TRIMIS|LUCRAT|RECOLTAT|GENERAT|Pagina|Rezultatele|"
    r"Reproducerea|Pentru|Nu se|Este|Valori|Opiniile|Analizele|Se utilizeaz|"
    r"http|F01|F-0|Ed\.|rev\.|bioclinica|VALORI|medic\s+primar|18\.02\.|29\.05\.|"
    r"brasov@|RENAR|seria|serie|Nr\.\s+\d|Buletin de analize|Data tipar|"
    r"Test Rezultat|Hematologie|Electroforeza|Validat|Verificat|PORUMBOI|"
    r"MEDIC |COD:|Sange |Ser,|Ser\.|Intr-un|Probele|Se interzice|Registrul|"
    r"Activitate|Analize neacreditate|Opinii|Rezultatele examinarilor|"
    r"Probele biologice|acreditat|Policlinica|Laborator de|eMail|Corp Central|"
    r"Aripa de|Jud\.|Loc\.|Telefon program|Punct recoltare|Adresa:|Telefon:|"
    r"Cod client|Cod proba|Cod caz|Varsta|Sex:|Prenume:|Nume:|Medic:|Cabinet|"
    # Antete sectiuni laborator
    r"HEMOLEUCOGRAMA|BIOCHIMIE|IMUNOLOGIE|HORMONI|SUMAR URINA|COAGULARE|"
    r"LIPIDOGRAMA|ELECTROFOREZA|SEROLOGIE|MARKERI|MINERALE|"
    # Note de clasificare (ex: "Crescut : 160-189", "Acceptabil: < 110")
    r"Acceptabil\s*:|Borderline|Crescut\s*[:\(]|Foarte\s+crescut|"
    r"Usor\s+crescut|Moderat\s+crescut|crescute?\s*[>:]|"
    r"Normal\s*:|Optim\s*:|Risc\s*:|Deficit\s+|Nivel\s+toxic|"
    # Note cu varsta/trimestru
    r"\d{1,3}-\d{1,3}\s+ani|peste\s+\d+\s+ani|trimest|"
    r"persoanelor|persoane\s+varst|"
    # Note diagnostice
    r"Diagnosticul|Glicemie\s+bazala\s+modif|Se\s+recomanda\s+retest|"
    # Artefacte OCR si certificate
    r"Regulamentul\s+nr|CERTIFICAT|certificat|Seria\s+[A-Z]|Nr\.\s+[A-Z]|"
    # Linii administrative laborator
    r"Cod\s+Cerere|Cod\s+Proba|Formular:|Act:\s+[A-Z]|Cont:\s+RO|"
    r"uz\s+personal|executate\s+de\s+parteneri|ghidului\s+KDIGO|"
    r"Data\s+nasterii|Spectrofotome|CITOMETRIE|Raspuns\s+rapid|"
    r"amoxicillin|Cefuroxime|diabet\s+zaharat|"
    r"Bacteriurie|Corpi\s+cetonici|Nitri[ti]|Leucociturie|"
    r"RETEAUA\s+PRIVATA|RETEA\s+PRIVAT|Regina\s+Maria|REGINA\s+MARIA|"
    r"Punct\s+de\s+lucru|Cod\s+de\s+bare|Cod:|Coad:|PD\s+\d|"
    r"Data\s+-\s+ora\s+recolt|ora\s+recoltare|Data\s+recoltare|"
    # Intervale referinta si clasificari
    r"Usor\s+crescut|Moderat\s+crescut|Foarte\s+crescut|"
    r"Optim\s*:|Normal\s*:|Diabet\s+|Glicemie\s+bazala|"
    r"trimestrul|trimester\s+[I]|20-40\s+ani|peste\s+40\s+ani|"
    r"eGFR:\s*[<>]|G1\s+=|G2\s+=|G3|G4|G5|"
    # Linii scurte care incep cu punct/doua puncte/spatiu (artefacte tabele)
    r":\s*[a-z]\s+[a-z]|^\s*[:\.\-]\s)",
    re.IGNORECASE,
)

_LINIE_NOTA = re.compile(r"^\(|^\s*\(")

# Format Bioclinica: valoare+unitate + interval in paranteza
RE_VALOARE_LINIE = re.compile(
    r"^([\d.,]+)\s*([a-zA-Z/%µμg·²³\s/]+?)\s*\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)

# Format valoare simpla fara interval
RE_VALOARE_PARTIAL = re.compile(
    r"^([\d.,]+)\s*([a-zA-Z/%µμg·²³\s/m]+?)$",
    re.IGNORECASE,
)


def validare_cnp(cnp: str) -> bool:
    if not re.match(r"^[1-8]\d{12}$", cnp):
        return False
    s = sum(int(cnp[i]) * CNP_CONTROL[i] for i in range(12)) % 11
    if s == 10:
        s = 1
    return s == int(cnp[12])


def extract_cnp(text: str) -> Optional[str]:
    for m in re.finditer(r"\b[1-8]\d{12}\b", text):
        if validare_cnp(m.group()):
            return m.group()
    return None


def extract_nume(text: str) -> tuple[str, Optional[str]]:
    """
    Incearca mai intai formatele explicite 'Nume:' + 'Prenume:' (MedLife, Synevo etc.).
    Dupa aceea cauta backward de la CNP (format Bioclinica).
    """
    # --- Varianta 1: linii explicite Nume: / Prenume: ---
    m_n = re.search(r"(?:^|\n)\s*Nume\s*:\s*([^\n]+)", text, re.IGNORECASE)
    m_p = re.search(r"(?:^|\n)\s*Prenume\s*:\s*([^\n]+)", text, re.IGNORECASE)
    if m_n:
        raw_n = m_n.group(1).strip()
        # Taie la primul cuvant-cheie care nu face parte din nume
        raw_n = re.split(
            r"\s+(?:Medic|Data|Cabinet|Sex|Varsta|Cod|Adresa|Telefon|Punctul|Punct)\s*[:\s]",
            raw_n, maxsplit=1, flags=re.IGNORECASE
        )[0].strip()
        # Curata artefacte OCR de la sfarsit (ex. "ol", "cl" etc.)
        raw_n = re.sub(r"\s+[a-z]{1,2}\s*$", "", raw_n).strip()

        prenume = None
        if m_p:
            raw_p = m_p.group(1).strip()
            raw_p = re.split(
                r"\s+(?:Medic|Data|Cabinet|Sex|Varsta|Cod|Adresa|Telefon|Punctul|Punct)\s*[:\s]",
                raw_p, maxsplit=1, flags=re.IGNORECASE
            )[0].strip()
            # Curata artefact OCR "ol" de la sfarsit
            raw_p = re.sub(r"\s+ol\s*$", "", raw_p, flags=re.IGNORECASE).strip()
            raw_p = re.sub(r"\s+[a-z]{1,2}\s*$", "", raw_p).strip()
            prenume = raw_p if raw_p else None
            if prenume:
                return f"{raw_n} {prenume}", prenume

        return raw_n, prenume

    # --- Varianta 2: backward de la CNP (format Bioclinica) ---
    m_cnp = re.search(r"\bCNP\s*:?\s*[1-8]\d{12}\b", text)
    if m_cnp:
        before = text[:m_cnp.start()].strip()
        lines_before = [l.strip() for l in before.split("\n") if l.strip()]
        for linie in reversed(lines_before):
            if re.match(r"^[\d\(]", linie):
                continue
            if _LINII_EXCLUSE.match(linie):
                continue
            clean = re.sub(r"\s+[FM],\s*\d+\s*(luni|ani)\s*$", "", linie, flags=re.IGNORECASE).strip()
            if re.search(r"\b[A-ZȘȚĂÂÎ]{2,}", clean):
                parts = clean.split(None, 1)
                return clean, parts[1] if len(parts) >= 2 else None

    # --- Varianta 3: fallback generic ---
    for pat in [r"(?:Pacient|Beneficiar)\s*[:\-]\s*([^\n]+)"]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            parts = raw.split(None, 1)
            return raw, parts[1] if len(parts) >= 2 else None

    return "Necunoscut", None


def _este_linie_parametru(linie: str) -> bool:
    if not linie or len(linie) > 150:
        return False
    if _LINII_EXCLUSE.match(linie):
        return False
    if _LINIE_NOTA.match(linie):
        return False
    if re.search(r"\d{9,}", linie):
        return False
    if re.match(r"^\d{2}\.\d{2}\.\d{4}", linie):
        return False
    # Linii care incep cu semne de punctuatie sau caractere speciale (artefacte tabele)
    if re.match(r'^["\'\[\]\{\}:;|\\]', linie):
        return False
    # Linii de clasificare/referinta: "Ceva: < 60", "eGFR: = 142", "k = 0.7"
    # Detecteaza pattern: text_scurt ':' optional_spatiu operator_sau_numar
    if re.search(r':\s*[<>=≤≥]\s*\d', linie):
        return False
    # Linii cu text foarte scurt si ambiguu (< 4 caractere utile)
    if len(re.sub(r'[^a-zA-Z]', '', linie)) < 3:
        return False
    # Linii care incep cu numar de linie (ex: "9.3 Alfa2-globuline%", "1. Hemoglobina")
    # dar NU linii care incep cu valori medicale cunoscute (ex: "25-OH Vitamina D")
    if re.match(r'^\d+\.\d+\s+[A-Z]', linie):
        # Sterge prefixul numeric si continua parsarea cu restul
        linie_fara_prefix = re.sub(r'^\d+\.\d+\s+\*?\s*', '', linie).strip()
        if linie_fara_prefix != linie:
            return _este_linie_parametru(linie_fara_prefix)
    return True


def _parse_oneline(linie: str) -> Optional[RezultatParsat]:
    """
    Parseaza o linie de forma:  NumeAnaliza  Valoare  UM  [Min-Max [UM]] [flag]
    Exemple:
      Hemoglobina 16.4 g/dL 13.0-17.0 g/dl
      Hematocrit 49.1 % 40-50%
      CRP cantitativ 187 mg/L 0-5 mgii
      RDW-CV 144 % 11.5-145%
    """
    linie = linie.strip()
    if not linie:
        return None

    # Elimina prefix numeric de linie (ex: "9.3 Alfa2-globuline%" -> "Alfa2-globuline%")
    linie = re.sub(r'^\d+\.\d+\s+\*?\s*', '', linie).strip()
    if not linie:
        return None

    # Gaseste primul numar izolat (valoarea) - nu face parte din nume
    # Numele poate contine cifre, dar valoarea e un numar singur dupa spatiu
    m_val = re.search(
        r"(?<!\S)(\d+[.,]\d+|\d+)\s+"        # valoare numerica
        r"([a-zA-Z%µμg·²³'\/][a-zA-Z0-9%µμg·²³'\/\*\.]*)"  # unitate (incepe cu litera/%)
        r"(?:\s+|$)",
        linie
    )
    if not m_val:
        return None

    name = linie[:m_val.start()].strip()
    if not name or len(name) < 2:
        return None

    # Curata artefacte OCR din nume (ghilimele, asteriscuri la inceput)
    name = re.sub(r'^["\'\*%\s]+', '', name).strip()
    if not name or len(name) < 2:
        return None

    # Daca "numele" este doar un numar (ex: "14.2" care e de fapt limita inf referinta),
    # nu este o denumire valida de analiza
    if re.match(r'^\d+[.,]?\d*\s*$', name):
        return None

    try:
        valoare = float(m_val.group(1).replace(",", "."))
    except ValueError:
        return None

    unitate = m_val.group(2) or None
    # Curata unitati cu artefacte OCR (ex. g/'dL → g/dL)
    if unitate:
        unitate = re.sub(r"['\"]", "", unitate).strip() or None

    # Cauta intervalul in restul liniei
    rest = linie[m_val.end():]
    m_interval = re.search(r"([\d.,]+)\s*[-–]\s*([\d.,]+)", rest)
    interval_min = interval_max = None
    if m_interval:
        try:
            interval_min = float(m_interval.group(1).replace(",", "."))
            interval_max = float(m_interval.group(2).replace(",", "."))
        except ValueError:
            pass

    # Valideaza interval (interval_min trebuie < interval_max)
    if interval_min is not None and interval_max is not None:
        if interval_min >= interval_max:
            interval_min = interval_max = None

    # Corecteaza erori OCR punct zecimal pierdut (ex: 9.9 citit ca 99)
    valoare = _corecteaza_decimal_pierdut(valoare, interval_min, interval_max)

    # Flag H/L — mai intai explicit din text, apoi calculat din interval
    flag = None
    if re.search(r"\bH\b", rest):
        flag = "H"
    elif re.search(r"\bL\b", rest):
        flag = "L"
    elif valoare is not None and interval_min is not None and interval_max is not None:
        if valoare > interval_max:
            flag = "H"
        elif valoare < interval_min:
            flag = "L"

    return RezultatParsat(
        denumire_raw=name,
        valoare=valoare,
        unitate=unitate,
        interval_min=interval_min,
        interval_max=interval_max,
        flag=flag,
    )


def _corecteaza_decimal_pierdut(valoare: float, interval_min, interval_max) -> float:
    """
    Corecteaza erori OCR de tipul '9.9 -> 99' (punct zecimal pierdut).
    Daca valoarea e > 10x intervalul_max si valoarea/10 e in interval,
    inseamna ca OCR a omis punctul zecimal.
    """
    if interval_max is None or interval_max <= 0:
        return valoare
    if valoare > 10 * interval_max:
        v_corectat = valoare / 10
        # Valoarea corectata trebuie sa fie cel mult de 2x interval_max
        if v_corectat <= 2 * interval_max:
            return v_corectat
    return valoare


def extract_rezultate(text: str) -> list[RezultatParsat]:
    """
    Extrage analizele din text. Suporta:
    - Format Bioclinica (2 linii): parametru pe linia i, valoare+UM+interval pe linia i+1
    - Format MedLife/generic (1 linie): parametru + valoare + UM + interval pe aceeasi linie
    """
    lines = [l.strip() for l in text.replace("\r", "\n").split("\n")]
    results: list[RezultatParsat] = []
    seen: set = set()

    def _add(r: Optional[RezultatParsat]) -> None:
        if r is None:
            return
        key = (r.denumire_raw[:80].lower(), round(r.valoare, 3))
        if key not in seen:
            seen.add(key)
            results.append(r)

    # --- Pasul 1: format doua linii Bioclinica ---
    for i in range(1, len(lines)):
        linie_val = lines[i]
        if not linie_val:
            continue
        m = RE_VALOARE_LINIE.match(linie_val)
        if not m:
            continue
        try:
            valoare = float(m.group(1).replace(",", "."))
        except ValueError:
            continue
        unitate = m.group(2).strip().replace(" ", "") or None
        try:
            interval_min = float(m.group(3).replace(",", "."))
            interval_max = float(m.group(4).replace(",", "."))
            # Valideaza intervalul (min trebuie sa fie < max)
            if interval_min >= interval_max:
                interval_min = interval_max = None
        except ValueError:
            interval_min = interval_max = None
        denumire = ""
        for j in range(i - 1, max(i - 4, -1), -1):
            cand = lines[j].strip()
            if not cand or _LINIE_NOTA.match(cand):
                continue
            if _este_linie_parametru(cand) and not RE_VALOARE_LINIE.match(cand) and not RE_VALOARE_PARTIAL.match(cand):
                denumire = cand
            break
        if not denumire:
            continue
        # Corecteaza erori OCR punct zecimal pierdut (ex: 9.9 fL citit ca 99)
        valoare = _corecteaza_decimal_pierdut(valoare, interval_min, interval_max)
        flag_calc = None
        if interval_min is not None and interval_max is not None:
            if valoare > interval_max:
                flag_calc = "H"
            elif valoare < interval_min:
                flag_calc = "L"
        _add(RezultatParsat(
            denumire_raw=denumire,
            valoare=valoare,
            unitate=unitate,
            interval_min=interval_min,
            interval_max=interval_max,
            flag=flag_calc,
        ))

    # --- Pasul 2: format un singur rand (MedLife, Synevo etc.) ---
    for linie in lines:
        if not _este_linie_parametru(linie):
            continue
        _add(_parse_oneline(linie))

    return results


def parse_full_text(text: str) -> Optional[PatientParsed]:
    cnp = extract_cnp(text)
    if not cnp:
        return None
    nume, prenume = extract_nume(text)
    rezultate = extract_rezultate(text)
    return PatientParsed(cnp=cnp, nume=nume or "Necunoscut", prenume=prenume, rezultate=rezultate)
