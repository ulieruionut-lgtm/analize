"""FastAPI – Analize medicale PDF. Interfata medic + API REST."""
import os
import re
import tempfile
import traceback
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse

from config import settings
from database import (
    get_pacient_cu_analize,
    get_all_pacienti,
    search_pacienti,
    get_all_analize_standard,
    get_historicul_analiza,
    get_historicul_analiza_by_cod,
    get_analize_necunoscute,
    sterge_analiza_necunoscuta,
    insert_buletin,
    insert_rezultat,
    upsert_pacient,
)
from models import PatientParsed
from normalizer import normalize_rezultate
from parser import parse_full_text
from pdf_processor import extract_text_from_pdf

app = FastAPI(title="Analize medicale PDF", version="1.0.0")

_ERORI_LOG = Path(__file__).resolve().parent.parent / "upload_eroare.txt"


def _raspuns_eroare(status: int, mesaj: str):
    return JSONResponse(
        status_code=status,
        content={"detail": mesaj[:500]},
        media_type="application/json",
    )


def _normalizare_data_text(raw: str) -> str:
    """Normalizeaza data ca DD.MM.YYYY (fara ora)."""
    raw = (raw or "").strip()
    raw = raw.replace("/", ".").replace("-", ".")
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", raw)
    if m:
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    m = re.match(r"^(\d{4})\.(\d{2})\.(\d{2})$", raw)
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
    return raw[:10]


def _extrage_data_buletin(text: str) -> Optional[str]:
    """
    Extrage data reala din buletin (fara ora).
    Prioritate: Data emitere -> Data buletin -> Data recoltare -> prima data valida.
    """
    if not text:
        return None
    patterns = [
        r"Data\s+emitere\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"Data\s+buletin(?:ului)?\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"Data\s+recoltare\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b",
        r"\b(\d{4}[./-]\d{2}[./-]\d{2})\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return _normalizare_data_text(m.group(1))
    return None


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    return _raspuns_eroare(422, "Date invalide: " + str(exc.errors())[:300])


@app.exception_handler(Exception)
async def json_exception_handler(request, exc):
    try:
        _ERORI_LOG.write_text(traceback.format_exc(), encoding="utf-8")
    except Exception:
        pass
    if isinstance(exc, HTTPException):
        return _raspuns_eroare(exc.status_code, str(exc.detail))
    return _raspuns_eroare(500, "Eroare server: " + str(exc))


@app.middleware("http")
async def catch_all_errors(request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        try:
            _ERORI_LOG.write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        return _raspuns_eroare(500, str(e))


# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    try:
        from database import get_cursor
        with get_cursor() as cur:
            cur.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return JSONResponse(content={"status": "error", "database": str(e)}, status_code=503)


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Primeste PDF, extrage text (sau OCR), parseaza CNP + nume + analize, salveaza in DB."""
    tmp_path = None
    try:
        if not file or not file.filename or not file.filename.lower().endswith(".pdf"):
            return JSONResponse(status_code=400, content={"detail": "Fisierul trebuie sa fie PDF."})
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        text, tip, ocr_err = extract_text_from_pdf(tmp_path)
        if not text or len(text.strip()) < 10:
            detail = "Nu s-a putut extrage text din PDF (gol sau prea scurt)."
            if ocr_err:
                detail += " " + str(ocr_err)
            return JSONResponse(status_code=422, content={"detail": detail})
        parsed: Optional[PatientParsed] = parse_full_text(text)
        if not parsed:
            return JSONResponse(status_code=422, content={"detail": "Nu s-a gasit un CNP valid in PDF."})
        normalize_rezultate(parsed.rezultate)
        pacient = upsert_pacient(parsed.cnp, parsed.nume, parsed.prenume)
        data_buletin = _extrage_data_buletin(text)
        buletin = insert_buletin(
            pacient_id=pacient["id"],
            data_buletin=data_buletin,
            laborator=None,
            fisier_original=file.filename,
        )
        for r in parsed.rezultate:
            insert_rezultat(
                buletin_id=buletin["id"],
                analiza_standard_id=r.analiza_standard_id,
                denumire_raw=r.denumire_raw,
                valoare=r.valoare,
                valoare_text=r.valoare_text,
                unitate=r.unitate,
                interval_min=r.interval_min,
                interval_max=r.interval_max,
                flag=r.flag,
            )
        return {
            "message": "PDF procesat cu succes.",
            "tip_extragere": tip,
            "pacient": {"id": pacient["id"], "cnp": pacient["cnp"], "nume": pacient["nume"], "prenume": pacient.get("prenume")},
            "buletin_id": buletin["id"],
            "data_buletin": buletin.get("data_buletin"),
            "numar_analize": len(parsed.rezultate),
        }
    except Exception as e:
        try:
            _ERORI_LOG.write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        detail = str(e)
        status = 503 if ("connection" in detail.lower() or "role" in detail or "database" in detail.lower()) else 500
        return _raspuns_eroare(status, detail)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@app.get("/pacienti")
async def lista_pacienti(q: Optional[str] = None):
    """Lista pacienti. Optional: ?q=text pentru cautare dupa CNP sau Nume."""
    if q and q.strip():
        return search_pacienti(q.strip())
    return get_all_pacienti()


@app.get("/pacient/{cnp}/evolutie-matrice")
async def get_pacient_evolutie_matrice(cnp: str):
    """
    Returneaza matricea de evolutie pentru pacient: analize pe randuri, date pe coloane.
    Format: {pacient: {...}, date_buletine: [...], analize: [{denumire, unitate, valori[], flags[]}]}
    """
    pacient_data = get_pacient_cu_analize(cnp)
    if not pacient_data:
        raise HTTPException(status_code=404, detail="Pacient negasit.")
    
    # 1. Extrage toate buletinele si sorteaza descrescator (cel mai recent la stanga)
    buletine = pacient_data.get("buletine", [])
    buletine_sorted = sorted(
        buletine,
        key=lambda b: (b.get("data_buletin") or b.get("created_at") or ""),
        reverse=True
    )
    
    # 2. Construieste lista de date (coloane)
    date_buletine = []
    for b in buletine_sorted:
        data = b.get("data_buletin") or b.get("created_at") or ""
        # Normalizeaza data ca DD.MM.YYYY
        if data:
            # Daca contine timestamp (T sau spatiu + ora), elimina-l
            if "T" in data:
                data = data.split("T")[0]
            elif " " in data and ":" in data:
                data = data.split(" ")[0]
            # Aplica normalizare
            data = _normalizare_data_text(data)
        date_buletine.append(data or "Necunoscuta")
    
    # 3. Grupeaza rezultatele pe analiza_standard
    # cheie = (analiza_standard_id, denumire_standard) sau (None, denumire_raw)
    analize_map = {}  # cheie -> {denumire, unitate, valori_dict: {buletin_id: (valoare, flag)}}
    
    for idx_buletin, b in enumerate(buletine_sorted):
        buletin_id = b.get("id")
        for rez in b.get("rezultate", []):
            # Cheie de grupare: folosim analiza_standard_id sau denumire_raw
            if rez.get("analiza_standard_id"):
                cheie = (rez["analiza_standard_id"], rez.get("denumire_standard") or rez.get("denumire_raw", ""))
            else:
                cheie = (None, rez.get("denumire_raw", "Necunoscuta"))
            
            if cheie not in analize_map:
                analize_map[cheie] = {
                    "denumire_standard": cheie[1],
                    "unitate": rez.get("unitate") or "",
                    "valori_dict": {}
                }
            
            # Salveaza valoarea pentru acest buletin
            valoare = rez.get("valoare")
            if valoare is None and rez.get("valoare_text"):
                valoare = rez.get("valoare_text")
            
            analize_map[cheie]["valori_dict"][buletin_id] = (valoare, rez.get("flag") or "")
    
    # 4. Construieste lista finala de analize cu vectori de valori
    analize_result = []
    for cheie in sorted(analize_map.keys(), key=lambda k: k[1].lower()):
        info = analize_map[cheie]
        valori = []
        flags = []
        for b in buletine_sorted:
            bid = b.get("id")
            if bid in info["valori_dict"]:
                val, flag = info["valori_dict"][bid]
                valori.append(val)
                flags.append(flag)
            else:
                valori.append(None)
                flags.append("")
        
        analize_result.append({
            "denumire_standard": info["denumire_standard"],
            "unitate": info["unitate"],
            "valori": valori,
            "flags": flags
        })
    
    return {
        "pacient": {
            "cnp": pacient_data.get("cnp"),
            "nume": pacient_data.get("nume"),
            "prenume": pacient_data.get("prenume")
        },
        "date_buletine": date_buletine,
        "analize": analize_result
    }


@app.get("/pacient/{cnp}")
async def get_pacient(cnp: str):
    """Pacientul cu CNP dat + toate buletinele + rezultatele."""
    result = get_pacient_cu_analize(cnp)
    if not result:
        raise HTTPException(status_code=404, detail="Pacient negasit.")
    return result


@app.get("/analize-standard")
async def lista_analize_standard():
    """Lista tuturor tipurilor de analize din baza de date."""
    return get_all_analize_standard()


@app.get("/analize-necunoscute")
async def lista_necunoscute(toate: bool = False):
    """Analize nerecunoscute de normalizer (neaprobate sau toate)."""
    return get_analize_necunoscute(doar_neaprobate=not toate)


@app.post("/aproba-alias")
async def aproba_alias(body: dict):
    """
    Aprobare alias: asociaza o denumire_raw necunoscuta cu o analiza_standard.
    Body: { "denumire_raw": "...", "analiza_standard_id": 5 }
    """
    raw = (body.get("denumire_raw") or "").strip()
    aid = body.get("analiza_standard_id")
    if not raw or not aid:
        return JSONResponse(status_code=400, content={"detail": "Campuri obligatorii: denumire_raw, analiza_standard_id"})
    from normalizer import adauga_alias_nou
    ok = adauga_alias_nou(raw, int(aid))
    if ok:
        return {"ok": True, "mesaj": f"Alias '{raw}' asociat cu succes."}
    return JSONResponse(status_code=500, content={"detail": "Eroare la salvarea alias-ului."})


@app.delete("/analiza-necunoscuta/{id_nec}")
async def sterge_necunoscuta(id_nec: int):
    """Sterge o analiza necunoscuta (ex: zgomot, artefact OCR)."""
    sterge_analiza_necunoscuta(id_nec)
    return {"ok": True}


@app.get("/analiza-historicul/{analiza_id}")
async def historicul_analiza(analiza_id: int):
    """Toate rezultatele pentru un tip de analiza (dupa id), de la toti pacientii."""
    rezultate = get_historicul_analiza(analiza_id)
    return {"analiza_id": analiza_id, "rezultate": rezultate, "total": len(rezultate)}


# ─── Interfata HTML Medic ─────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    html = r"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Analize Medicale – Panou Medic</title>
<style>
  :root {
    --albastru: #1a73e8;
    --albastru-deschis: #e8f0fe;
    --verde: #0f9d58;
    --rosu: #d93025;
    --portocaliu: #f9ab00;
    --gri: #5f6368;
    --gri-deschis: #f1f3f4;
    --alb: #ffffff;
    --border: #dadce0;
    --shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; background: #f8f9fa; color: #202124; }

  /* Header */
  .header {
    background: var(--albastru);
    color: white;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: var(--shadow);
    position: sticky; top: 0; z-index: 100;
  }
  .header h1 { font-size: 1.2rem; font-weight: 500; }
  .header .sub { font-size: 0.8rem; opacity: 0.85; }

  /* Tabs */
  .tabs {
    display: flex;
    background: white;
    border-bottom: 2px solid var(--border);
    padding: 0 24px;
    gap: 4px;
  }
  .tab-btn {
    padding: 14px 20px;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 0.9rem;
    color: var(--gri);
    font-weight: 500;
    border-bottom: 3px solid transparent;
    margin-bottom: -2px;
    transition: all 0.2s;
  }
  .tab-btn:hover { color: var(--albastru); background: var(--albastru-deschis); border-radius: 8px 8px 0 0; }
  .tab-btn.activ { color: var(--albastru); border-bottom-color: var(--albastru); }

  /* Content */
  .content { max-width: 1100px; margin: 0 auto; padding: 24px; }
  .sectiune { display: none; }
  .sectiune.activa { display: block; }

  /* Card */
  .card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: var(--shadow);
    margin-bottom: 20px;
  }
  .card h2 { font-size: 1.05rem; color: var(--gri); margin-bottom: 16px; font-weight: 500; }

  /* Upload zone */
  .upload-zone {
    border: 2px dashed var(--border);
    border-radius: 12px;
    padding: 40px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
  }
  .upload-zone:hover, .upload-zone.drag-over {
    border-color: var(--albastru);
    background: var(--albastru-deschis);
  }
  .upload-icon { font-size: 3rem; margin-bottom: 12px; }
  .upload-zone p { color: var(--gri); font-size: 0.95rem; }
  #file-input { display: none; }
  #file-name { margin-top: 10px; font-weight: 500; color: var(--albastru); }

  /* Butoane */
  .btn {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 10px 22px;
    border: none; border-radius: 6px;
    font-size: 0.9rem; font-weight: 500;
    cursor: pointer; transition: all 0.2s;
  }
  .btn-primary { background: var(--albastru); color: white; }
  .btn-primary:hover { background: #1557b0; }
  .btn-primary:disabled { background: #9aa0a6; cursor: default; }
  .btn-secondary { background: var(--gri-deschis); color: var(--gri); }
  .btn-secondary:hover { background: var(--border); }

  /* Mesaje */
  .mesaj { padding: 14px 18px; border-radius: 8px; margin-top: 14px; font-size: 0.9rem; }
  .mesaj.succes { background: #e6f4ea; color: #137333; border-left: 4px solid var(--verde); }
  .mesaj.eroare { background: #fce8e6; color: #c5221f; border-left: 4px solid var(--rosu); }
  .mesaj.info { background: var(--albastru-deschis); color: #174ea6; border-left: 4px solid var(--albastru); }
  .mesaj strong { display: block; margin-bottom: 4px; }

  /* Spinner */
  .spinner {
    display: inline-block; width: 18px; height: 18px;
    border: 2px solid rgba(255,255,255,0.4);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* Search */
  .search-row { display: flex; gap: 10px; margin-bottom: 20px; }
  .input-search {
    flex: 1; padding: 10px 16px;
    border: 1px solid var(--border);
    border-radius: 8px; font-size: 0.95rem;
    outline: none; transition: border 0.2s;
  }
  .input-search:focus { border-color: var(--albastru); box-shadow: 0 0 0 3px rgba(26,115,232,0.15); }

  /* Tabel */
  .tabel-container { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
  th { background: var(--gri-deschis); padding: 10px 14px; text-align: left; font-weight: 600; color: var(--gri); border-bottom: 2px solid var(--border); }
  td { padding: 10px 14px; border-bottom: 1px solid var(--border); }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: var(--gri-deschis); }
  .badge {
    display: inline-block; padding: 2px 10px;
    border-radius: 12px; font-size: 0.78rem; font-weight: 600;
  }
  .badge-H { background: #fce8e6; color: #c5221f; }
  .badge-L { background: #e8f0fe; color: #1a73e8; }
  .badge-norm { background: #e6f4ea; color: #137333; }

  /* Pacient card */
  .pacient-header {
    display: flex; align-items: flex-start;
    gap: 20px; margin-bottom: 20px;
  }
  .pacient-avatar {
    width: 56px; height: 56px; border-radius: 50%;
    background: var(--albastru); color: white;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem; font-weight: 700; flex-shrink: 0;
  }
  .pacient-info h3 { font-size: 1.15rem; }
  .pacient-info p { color: var(--gri); font-size: 0.85rem; margin-top: 3px; }

  /* Buletin accordion */
  .buletin {
    border: 1px solid var(--border);
    border-radius: 8px; margin-bottom: 12px; overflow: hidden;
  }
  .buletin-header {
    padding: 12px 16px; background: var(--gri-deschis);
    cursor: pointer; display: flex; justify-content: space-between; align-items: center;
    font-weight: 500; font-size: 0.9rem;
  }
  .buletin-header:hover { background: var(--border); }
  .buletin-body { padding: 0; display: none; }
  .buletin-body.deschis { display: block; }

  /* Valoare in-/out-of-range */
  .val-H { color: var(--rosu); font-weight: 600; }
  .val-L { color: var(--albastru); font-weight: 600; }
  .val-ok { color: var(--verde); }

  /* Select */
  .select-analiza {
    width: 100%; padding: 10px 16px;
    border: 1px solid var(--border); border-radius: 8px;
    font-size: 0.95rem; margin-bottom: 20px;
    background: white; outline: none;
  }
  .select-analiza:focus { border-color: var(--albastru); }

  /* Link stil */
  .link-cnp { color: var(--albastru); cursor: pointer; text-decoration: underline; }

  /* Grafic mini-bars */
  .mini-bar-wrap { display: flex; align-items: center; gap: 8px; }
  .mini-bar-bg { flex: 1; height: 6px; background: var(--border); border-radius: 3px; position: relative; overflow: hidden; }
  .mini-bar-fill { height: 100%; border-radius: 3px; }

  /* Tabel evolutie (Tab 2 - Pacient) */
  .tabel-evolutie-container {
    overflow-x: auto;
    max-width: 100%;
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-top: 20px;
  }

  .tabel-evolutie {
    min-width: 800px;
    border-collapse: collapse;
    width: 100%;
  }

  .tabel-evolutie th {
    position: sticky;
    top: 0;
    background: var(--gri-deschis);
    font-weight: 600;
    padding: 12px;
    text-align: center;
    border: 1px solid var(--border);
    white-space: nowrap;
    z-index: 1;
  }

  .tabel-evolutie .col-analiza {
    position: sticky;
    left: 0;
    background: white;
    font-weight: 600;
    text-align: left;
    min-width: 220px;
    max-width: 300px;
    z-index: 2;
  }

  .tabel-evolutie thead .col-analiza {
    background: var(--gri-deschis);
    z-index: 3;
  }

  .tabel-evolutie td {
    padding: 10px 12px;
    text-align: center;
    border: 1px solid var(--border);
    white-space: nowrap;
  }

  .tabel-evolutie tbody tr:hover {
    background: var(--albastru-deschis);
  }

  .tabel-evolutie tbody tr:hover .col-analiza {
    background: var(--albastru-deschis);
  }

  @media (max-width: 600px) {
    .content { padding: 12px; }
    .tabs { overflow-x: auto; }
    .search-row { flex-direction: column; }
  }
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>🏥 Analize Medicale</h1>
    <div class="sub">Panou medic – v22.02.2026</div>
  </div>
</div>

<div class="tabs">
  <button class="tab-btn activ" onclick="schimbTab('upload')">📤 Upload PDF</button>
  <button class="tab-btn" onclick="schimbTab('pacient')">👤 Pacient</button>
  <button class="tab-btn" onclick="schimbTab('analiza')">📊 Tip Analiză</button>
  <button class="tab-btn" id="tab-btn-alias" onclick="schimbTab('alias')">🔗 Analize necunoscute <span id="badge-nec" style="display:none;background:var(--rosu);color:white;border-radius:10px;padding:1px 7px;font-size:0.75rem;margin-left:4px">0</span></button>
</div>

<div class="content">

  <!-- TAB 1: Upload -->
  <div id="tab-upload" class="sectiune activa">
    <div class="card">
      <h2>Încarcă buletin PDF</h2>
      <div class="upload-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
        <div class="upload-icon">📄</div>
        <p>Trage fișierul PDF aici sau <strong>click</strong> pentru a selecta</p>
        <p style="font-size:0.8rem;margin-top:6px;color:#9aa0a6">Suportă PDF text și PDF scanat (OCR automat)</p>
        <div id="file-name"></div>
      </div>
      <input type="file" id="file-input" accept=".pdf">
      <div style="margin-top:16px; display:flex; gap:12px; align-items:center;">
        <button class="btn btn-primary" id="btn-upload" onclick="trimite()" disabled>
          <span id="btn-text">Procesează PDF</span>
        </button>
        <span id="prog" style="font-size:0.85rem;color:var(--gri)"></span>
      </div>
      <div id="upload-out"></div>
    </div>
    <div class="card" id="card-pacienti-recenti" style="display:none">
      <h2>Pacienți procesați recent</h2>
      <div id="lista-recenti"></div>
    </div>
  </div>

  <!-- TAB 2: Pacient -->
  <div id="tab-pacient" class="sectiune">
    <div class="card">
      <h2>Caută pacient după CNP sau Nume</h2>
      <div class="search-row">
        <input class="input-search" id="q-pacient" placeholder="Introduceți CNP sau Nume…" oninput="cautaPacient(this.value)">
      </div>
      <div id="lista-pacienti"></div>
    </div>
    <div id="detaliu-pacient" style="display:none"></div>
  </div>

  <!-- TAB 3: Evolutie analiza pacient -->
  <div id="tab-analiza" class="sectiune">
    <div class="card">
      <h2>Evoluție analiză – pentru un pacient</h2>

      <!-- Pasul 1: cauta pacient -->
      <p style="font-size:0.85rem;color:var(--gri);margin-bottom:10px">
        <strong>Pas 1</strong> – Caută și selectează pacientul
      </p>
      <div class="search-row">
        <input class="input-search" id="q-analiza-pacient"
          placeholder="CNP sau Nume pacient…"
          oninput="cautaPacientPentruAnaliza(this.value)">
      </div>
      <div id="lista-pacienti-analiza"></div>
    </div>

    <!-- Pasul 2 + 3: apar dupa selectie pacient -->
    <div id="card-analiza-pacient" style="display:none" class="card">
      <div id="pacient-analiza-header" style="margin-bottom:16px"></div>

      <p style="font-size:0.85rem;color:var(--gri);margin-bottom:10px">
        <strong>Pas 2</strong> – Selectează analiza
      </p>
      <select class="select-analiza" id="sel-analiza-pacient" onchange="incarcaEvolPacient()">
        <option value="">— Selectați analiza —</option>
      </select>

      <div id="rezult-analiza"></div>
    </div>
  </div>

  <!-- TAB 4: Analize necunoscute -->
  <div id="tab-alias" class="sectiune">
    <div class="card">
      <h2>Analize nerecunoscute – asociere manuală</h2>
      <p style="font-size:0.88rem;color:var(--gri);margin-bottom:16px">
        Aceste analize au fost extrase din PDF-uri dar nu au fost recunoscute automat.<br>
        Asociați fiecare denumire cu analiza standard corespunzătoare.
        <strong>La următorul upload, vor fi recunoscute automat.</strong>
      </p>
      <div style="display:flex;gap:10px;margin-bottom:16px">
        <button class="btn btn-secondary" onclick="incarcaNecunoscute()">🔄 Reîncarcă lista</button>
      </div>
      <div id="lista-necunoscute"><p style="color:var(--gri)">Se încarcă…</p></div>
    </div>
  </div>

</div><!-- /content -->

<script>
// ─── Navigare tab-uri ─────────────────────────────────────────────────────────
function schimbTab(id) {
  document.querySelectorAll('.tab-btn').forEach((b,i) => b.classList.toggle('activ', ['upload','pacient','analiza','alias'][i] === id));
  document.querySelectorAll('.sectiune').forEach(s => s.classList.remove('activa'));
  document.getElementById('tab-' + id).classList.add('activa');
  if (id === 'pacient') incarcaListaPacienti('');
  if (id === 'alias') incarcaNecunoscute();
}

// ─── Upload ──────────────────────────────────────────────────────────────────
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
let fisierSelectat = null;

fileInput.onchange = e => selecteazaFisier(e.target.files[0]);

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  selecteazaFisier(e.dataTransfer.files[0]);
});

function selecteazaFisier(f) {
  if (!f) return;
  if (!f.name.toLowerCase().endsWith('.pdf')) {
    afiseazaMesaj('upload-out','eroare','Fișierul trebuie să fie PDF.');
    return;
  }
  fisierSelectat = f;
  document.getElementById('file-name').textContent = '📎 ' + f.name + ' (' + (f.size/1024).toFixed(1) + ' KB)';
  document.getElementById('btn-upload').disabled = false;
  document.getElementById('upload-out').innerHTML = '';
}

async function trimite() {
  if (!fisierSelectat) return;
  const btn = document.getElementById('btn-upload');
  const btnText = document.getElementById('btn-text');
  const prog = document.getElementById('prog');
  btn.disabled = true;
  btnText.innerHTML = '<span class="spinner"></span> Se procesează…';
  prog.textContent = fisierSelectat.name.toLowerCase().endsWith('.pdf') && fisierSelectat.size > 500000
    ? 'Fisier mare – poate dura 30-60 sec pentru scanat…' : '';

  const fd = new FormData();
  fd.append('file', fisierSelectat);
  try {
    const r = await fetch('/upload', { method: 'POST', body: fd });
    const text = await r.text();
    let j;
    try { j = JSON.parse(text); } catch { j = { detail: 'Raspuns invalid server: ' + text.substring(0,120) }; }

    if (r.ok) {
      const p = j.pacient || {};
      afiseazaMesaj('upload-out','succes',
        '<strong>✅ ' + j.message + '</strong>' +
        'Pacient: <strong>' + (p.nume||'') + '</strong> (CNP: ' + (p.cnp||'') + ')<br>' +
        'Tip extragere: ' + (j.tip_extragere==='ocr'?'🔍 OCR (scanat)':'📝 Text direct') +
        ' &nbsp;|&nbsp; Analize salvate: <strong>' + (j.numar_analize||0) + '</strong>' +
        '<br><br><button class="btn btn-secondary" onclick="veziPacient(\'' + (p.cnp||'') + '\')">👤 Vezi analizele pacientului</button>'
      );
      incarcaRecenti();
    } else {
      const msg = (j && j.detail) ? (Array.isArray(j.detail) ? j.detail.join(' ') : j.detail) : String(r.status);
      afiseazaMesaj('upload-out','eroare', '<strong>❌ Eroare:</strong>' + msg);
    }
  } catch(err) {
    afiseazaMesaj('upload-out','eroare','<strong>Eroare rețea:</strong>' + err.message);
  }
  btn.disabled = false;
  btnText.textContent = 'Procesează PDF';
  prog.textContent = '';
}

async function incarcaRecenti() {
  try {
    const r = await fetch('/pacienti');
    const lista = await r.json();
    if (!lista.length) return;
    document.getElementById('card-pacienti-recenti').style.display = '';
    const top5 = lista.slice(0,5);
    document.getElementById('lista-recenti').innerHTML =
      top5.map(p => `<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">
        <span><strong>${escHtml(p.nume||'')}</strong> <span style="color:var(--gri);font-size:0.82rem">CNP: ${escHtml(p.cnp)}</span></span>
        <button class="btn btn-secondary" style="padding:6px 14px;font-size:0.8rem" onclick="veziPacient('${escHtml(p.cnp)}')">Vezi</button>
      </div>`).join('');
  } catch {}
}

// ─── Pacient ─────────────────────────────────────────────────────────────────
let _cautaPacientTimer = null;
function cautaPacient(q) {
  clearTimeout(_cautaPacientTimer);
  _cautaPacientTimer = setTimeout(() => incarcaListaPacienti(q), 320);
}

async function incarcaListaPacienti(q) {
  const el = document.getElementById('lista-pacienti');
  el.innerHTML = '<span style="color:var(--gri);font-size:0.9rem">Se încarcă…</span>';
  try {
    const url = q ? '/pacienti?q=' + encodeURIComponent(q) : '/pacienti';
    const r = await fetch(url);
    const lista = await r.json();
    if (!lista.length) {
      el.innerHTML = '<p style="color:var(--gri);text-align:center;padding:20px">Niciun pacient găsit.</p>';
      return;
    }
    el.innerHTML = `<div class="tabel-container"><table>
      <thead><tr><th>Nume</th><th>CNP</th><th>Buletine</th><th>Acțiune</th></tr></thead>
      <tbody>` +
      lista.map(p => `<tr>
        <td><strong>${escHtml(p.nume||'')}</strong>${p.prenume?' <span style="color:var(--gri);font-size:0.82rem">'+escHtml(p.prenume)+'</span>':''}</td>
        <td style="font-family:monospace">${escHtml(p.cnp)}</td>
        <td><span class="badge badge-norm">${p.nr_buletine||0} buletin${p.nr_buletine==1?'':'e'}</span></td>
        <td><button class="btn btn-secondary" style="padding:6px 14px;font-size:0.82rem" onclick="veziPacient('${escHtml(p.cnp)}')">👤 Analize</button></td>
      </tr>`).join('') +
      '</tbody></table></div>';
  } catch(e) {
    el.innerHTML = '<p style="color:red">Eroare: ' + e.message + '</p>';
  }
}

async function veziPacient(cnp) {
  schimbTab('pacient');
  document.getElementById('q-pacient').value = cnp;
  const detaliu = document.getElementById('detaliu-pacient');
  detaliu.style.display = '';
  detaliu.innerHTML = '<div class="card"><p style="color:var(--gri)">Se încarcă datele pacientului…</p></div>';
  
  try {
    const r = await fetch('/pacient/' + encodeURIComponent(cnp) + '/evolutie-matrice');
    if (!r.ok) { 
      detaliu.innerHTML = '<div class="card"><p style="color:red">Pacientul nu a fost găsit.</p></div>'; 
      return; 
    }
    
    const data = await r.json();
    const initiale = (data.pacient.nume||'?').substring(0,1);
    
    // Header pacient
    let html = `<div class="card">
      <div class="pacient-header">
        <div class="pacient-avatar">${escHtml(initiale)}</div>
        <div class="pacient-info">
          <h3>${escHtml(data.pacient.nume||'')}${data.pacient.prenume?' '+escHtml(data.pacient.prenume):''}</h3>
          <p>CNP: <strong style="font-family:monospace">${escHtml(data.pacient.cnp)}</strong></p>
          <p>Buletine: <strong>${data.date_buletine.length}</strong> &nbsp;|&nbsp; Analize: <strong>${data.analize.length}</strong></p>
        </div>
      </div>`;
    
    if (!data.analize.length) {
      html += '<p style="color:var(--gri);padding:20px;text-align:center">Nicio analiză găsită pentru acest pacient.</p></div>';
      detaliu.innerHTML = html;
      return;
    }
    
    // Tabel evoluție
    html += '<div class="tabel-evolutie-container"><table class="tabel-evolutie">';
    
    // Header cu date
    html += '<thead><tr><th class="col-analiza">Tip Analize / Data</th>';
    data.date_buletine.forEach(d => {
      html += `<th>${escHtml(d)}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    // Rânduri analize
    data.analize.forEach(a => {
      html += '<tr><td class="col-analiza">';
      html += escHtml(a.denumire_standard);
      if (a.unitate) {
        html += ` <span style="color:var(--gri);font-size:0.85rem;font-weight:400">(${escHtml(a.unitate)})</span>`;
      }
      html += '</td>';
      
      a.valori.forEach((v, i) => {
        if (v == null) {
          html += '<td style="color:var(--gri)">—</td>';
        } else {
          const flag = a.flags[i] || '';
          const cls = flag === 'H' ? 'val-H' : flag === 'L' ? 'val-L' : 'val-ok';
          html += `<td class="${cls}"><strong>${v}</strong></td>`;
        }
      });
      html += '</tr>';
    });
    
    html += '</tbody></table></div></div>';
    detaliu.innerHTML = html;
    
  } catch(e) {
    detaliu.innerHTML = '<div class="card"><p style="color:red">Eroare: ' + e.message + '</p></div>';
  }
}

function toggleBuletin(id) {
  const el = document.getElementById('buletin-' + id);
  if (el) el.classList.toggle('deschis');
}

// ─── Tab 3: Evolutie analiza pentru un pacient ───────────────────────────────
let _pacientAnaliza = null;   // datele pacientului selectat in tab 3

let _cautaAnalizaTimer = null;
function cautaPacientPentruAnaliza(q) {
  clearTimeout(_cautaAnalizaTimer);
  _cautaAnalizaTimer = setTimeout(() => incarcaListaPacientiAnaliza(q), 320);
}

async function incarcaListaPacientiAnaliza(q) {
  const el = document.getElementById('lista-pacienti-analiza');
  if (!q || !q.trim()) { el.innerHTML = ''; return; }
  el.innerHTML = '<span style="color:var(--gri);font-size:0.9rem">Se caută…</span>';
  try {
    const r = await fetch('/pacienti?q=' + encodeURIComponent(q.trim()));
    const lista = await r.json();
    if (!lista.length) {
      el.innerHTML = '<p style="color:var(--gri);padding:12px 0">Niciun pacient găsit.</p>';
      return;
    }
    el.innerHTML = '<div class="tabel-container"><table>' +
      '<thead><tr><th>Nume</th><th>CNP</th><th>Buletine</th><th></th></tr></thead><tbody>' +
      lista.map(p => `<tr>
        <td><strong>${escHtml(p.nume||'')}</strong></td>
        <td style="font-family:monospace">${escHtml(p.cnp)}</td>
        <td>${p.nr_buletine||0}</td>
        <td><button class="btn btn-secondary" style="padding:6px 14px;font-size:0.82rem"
            onclick="selecteazaPacientAnaliza('${escHtml(p.cnp)}','${escHtml(p.nume||'')}')">Selectează</button></td>
      </tr>`).join('') +
      '</tbody></table></div>';
  } catch(e) {
    el.innerHTML = '<p style="color:red">' + e.message + '</p>';
  }
}

async function selecteazaPacientAnaliza(cnp, numeDisplay) {
  // Ascunde lista de cautare
  document.getElementById('lista-pacienti-analiza').innerHTML = '';
  document.getElementById('q-analiza-pacient').value = numeDisplay;

  const card = document.getElementById('card-analiza-pacient');
  const header = document.getElementById('pacient-analiza-header');
  const sel = document.getElementById('sel-analiza-pacient');
  const rezult = document.getElementById('rezult-analiza');

  card.style.display = '';
  rezult.innerHTML = '';
  header.innerHTML = '<p style="color:var(--gri);font-size:0.9rem">Se încarcă datele…</p>';

  try {
    const r = await fetch('/pacient/' + encodeURIComponent(cnp));
    if (!r.ok) { header.innerHTML = '<p style="color:red">Eroare la încărcare pacient.</p>'; return; }
    _pacientAnaliza = await r.json();

    // Header pacient
    const initiale = (_pacientAnaliza.nume||'?')[0];
    header.innerHTML = `
      <div class="pacient-header" style="margin-bottom:0">
        <div class="pacient-avatar">${escHtml(initiale)}</div>
        <div class="pacient-info">
          <h3>${escHtml(_pacientAnaliza.nume||'')}${_pacientAnaliza.prenume?' '+escHtml(_pacientAnaliza.prenume):''}</h3>
          <p>CNP: <strong style="font-family:monospace">${escHtml(_pacientAnaliza.cnp)}</strong>
          &nbsp;·&nbsp; ${(_pacientAnaliza.buletine||[]).length} buletine în baza de date</p>
        </div>
        <button class="btn btn-secondary" style="margin-left:auto;padding:6px 14px;font-size:0.82rem"
          onclick="resetTabAnaliza()">✕ Schimbă pacientul</button>
      </div>`;

    // Construieste lista de analize unice ale pacientului
    const analize = {};  // denumire_raw -> {list de rezultate}
    (_pacientAnaliza.buletine||[]).forEach(b => {
      (b.rezultate||[]).forEach(rz => {
        const cheie = rz.denumire_standard || rz.denumire_raw || '—';
        if (!analize[cheie]) analize[cheie] = [];
        analize[cheie].push({ ...rz, data_buletin: (b.data_buletin || b.created_at), fisier: b.fisier_original });
      });
    });

    // Populeza selectul cu analizele pacientului
    sel.innerHTML = '<option value="">— Selectați analiza —</option>';
    Object.keys(analize).sort().forEach(k => {
      const o = document.createElement('option');
      o.value = k;
      o.textContent = k + (analize[k].length > 1 ? ' (' + analize[k].length + ' rezultate)' : '');
      sel.appendChild(o);
    });

    // Salveaza harta
    sel._analize = analize;

  } catch(e) {
    header.innerHTML = '<p style="color:red">Eroare: ' + e.message + '</p>';
  }
}

function incarcaEvolPacient() {
  const sel = document.getElementById('sel-analiza-pacient');
  const el = document.getElementById('rezult-analiza');
  const cheie = sel.value;
  const analize = sel._analize || {};

  if (!cheie) { el.innerHTML = ''; return; }

  const lista = analize[cheie] || [];
  if (!lista.length) {
    el.innerHTML = '<p style="color:var(--gri);padding:16px 0">Niciun rezultat găsit.</p>';
    return;
  }

  // Sortare cronologica
  lista.sort((a,b) => (a.data_buletin||'') < (b.data_buletin||'') ? -1 : 1);

  const valori = lista.map(r => r.valoare).filter(v => v!=null);
  const vMin = Math.min(...valori), vMax = Math.max(...valori);
  const intervalRef = lista.find(r => r.interval_min!=null);

  let html = '';

  // Mini-grafic vizual daca sunt multiple valori
  if (valori.length > 1) {
    html += `<div style="margin-bottom:20px;padding:16px;background:var(--gri-deschis);border-radius:10px">
      <p style="font-size:0.82rem;color:var(--gri);margin-bottom:12px">
        Evoluție ${escHtml(cheie)}: min <strong>${Math.min(...valori)}</strong> → max <strong>${Math.max(...valori)}</strong>
        ${intervalRef?' &nbsp;|&nbsp; Interval normal: '+intervalRef.interval_min+' – '+intervalRef.interval_max+' '+escHtml(intervalRef.unitate||''):''}
      </p>
      <div style="display:flex;align-items:flex-end;gap:8px;height:70px">`;
    lista.forEach((r,i) => {
      if (r.valoare == null) return;
      const pct = vMax > vMin ? Math.max(10, ((r.valoare-vMin)/(vMax-vMin))*100) : 60;
      const col = r.flag==='H'?'var(--rosu)':r.flag==='L'?'var(--albastru)':'var(--verde)';
      const data = formatDateOnly(r.data_buletin) || ('Nr.'+(i+1));
      html += `<div style="display:flex;flex-direction:column;align-items:center;flex:1;gap:4px">
        <span style="font-size:0.72rem;font-weight:600;color:${col}">${r.valoare}</span>
        <div style="width:100%;height:${pct}%;background:${col};border-radius:4px 4px 0 0;min-height:6px"></div>
        <span style="font-size:0.68rem;color:var(--gri);text-align:center;white-space:nowrap">${escHtml(data)}</span>
      </div>`;
    });
    html += '</div></div>';
  }

  // Tabel detaliat
  html += `<div class="tabel-container"><table>
    <thead><tr><th>#</th><th>Data buletin</th><th>Fișier</th><th>Valoare</th><th>UM</th><th>Interval ref.</th><th>Status</th></tr></thead><tbody>` +
    lista.map((r,i) => {
      const cls = r.flag==='H'?'val-H':r.flag==='L'?'val-L':'val-ok';
      const badge = r.flag
        ? `<span class="badge badge-${r.flag}">${r.flag==='H'?'↑ Crescut':'↓ Scăzut'}</span>`
        : '<span class="badge badge-norm">Normal</span>';
      const interval = (r.interval_min!=null && r.interval_max!=null)
        ? r.interval_min + ' – ' + r.interval_max : '—';
      const data = formatDateOnly(r.data_buletin) || '—';
      return `<tr>
        <td style="color:var(--gri)">${i+1}</td>
        <td>${data}</td>
        <td style="font-size:0.82rem;color:var(--gri)">${escHtml(r.fisier||'')}</td>
        <td class="${cls}"><strong>${r.valoare!=null?r.valoare:escHtml(r.valoare_text||'—')}</strong></td>
        <td>${escHtml(r.unitate||'')}</td>
        <td style="color:var(--gri)">${interval}</td>
        <td>${badge}</td>
      </tr>`;
    }).join('') +
    '</tbody></table></div>';

  el.innerHTML = html;
}

function resetTabAnaliza() {
  _pacientAnaliza = null;
  document.getElementById('card-analiza-pacient').style.display = 'none';
  document.getElementById('q-analiza-pacient').value = '';
  document.getElementById('lista-pacienti-analiza').innerHTML = '';
  document.getElementById('rezult-analiza').innerHTML = '';
}

// ─── Tab 4: Analize necunoscute ───────────────────────────────────────────────
let _analize_std_cache = null;

async function incarcaStandardeCache() {
  if (_analize_std_cache) return _analize_std_cache;
  try {
    const r = await fetch('/analize-standard');
    _analize_std_cache = await r.json();
  } catch { _analize_std_cache = []; }
  return _analize_std_cache;
}

async function incarcaNecunoscute() {
  const el = document.getElementById('lista-necunoscute');
  el.innerHTML = '<p style="color:var(--gri)">Se încarcă…</p>';
  try {
    const [nec, std] = await Promise.all([
      fetch('/analize-necunoscute').then(r => r.json()),
      incarcaStandardeCache()
    ]);

    // Actualizeaza badge
    const badge = document.getElementById('badge-nec');
    if (nec.length > 0) {
      badge.textContent = nec.length;
      badge.style.display = '';
    } else {
      badge.style.display = 'none';
    }

    if (!nec.length) {
      el.innerHTML = '<div class="mesaj succes"><strong>✅ Toate analizele sunt recunoscute!</strong><br>Nicio analiză necunoscută în baza de date.</div>';
      return;
    }

    // Construieste optiunile pentru select
    const optStd = std.map(s => `<option value="${s.id}">${escHtml(s.denumire_standard)} (${escHtml(s.cod_standard)})</option>`).join('');

    el.innerHTML = `
      <p style="font-size:0.85rem;color:var(--gri);margin-bottom:12px">
        ${nec.length} analize nerecunoscute. Asociați-le cu analiza standard corectă:
      </p>
      <div class="tabel-container"><table>
      <thead><tr>
        <th>Denumire din PDF</th>
        <th>Apariții</th>
        <th>Asociază cu analiza standard</th>
        <th>Acțiuni</th>
      </tr></thead>
      <tbody>` +
      nec.map(n => `<tr id="nec-row-${n.id}">
        <td>
          <strong>${escHtml(n.denumire_raw)}</strong>
          <div style="font-size:0.75rem;color:var(--gri);margin-top:2px">Prima apariție: ${(n.created_at||'').substring(0,10)}</div>
        </td>
        <td><span class="badge badge-norm">${n.aparitii}×</span></td>
        <td>
          <select id="sel-std-${n.id}" style="width:100%;padding:6px 10px;border:1px solid var(--border);border-radius:6px;font-size:0.85rem">
            <option value="">— Selectați —</option>
            ${optStd}
          </select>
        </td>
        <td style="white-space:nowrap">
          <button class="btn btn-primary" style="padding:6px 12px;font-size:0.82rem;margin-right:4px"
            onclick="aprobaAlias(${n.id}, '${escHtml(n.denumire_raw).replace(/'/g,"\\'")}')">✓ Asociază</button>
          <button class="btn btn-secondary" style="padding:6px 10px;font-size:0.82rem"
            title="Șterge (zgomot / artefact OCR)"
            onclick="stergeNecunoscuta(${n.id})">🗑</button>
        </td>
      </tr>`).join('') +
      '</tbody></table></div>';

  } catch(e) {
    el.innerHTML = '<p style="color:red">Eroare: ' + e.message + '</p>';
  }
}

async function aprobaAlias(id, denumireRaw) {
  const sel = document.getElementById('sel-std-' + id);
  const aid = sel ? sel.value : '';
  if (!aid) { alert('Selectați mai întâi analiza standard!'); return; }

  try {
    const r = await fetch('/aproba-alias', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ denumire_raw: denumireRaw, analiza_standard_id: parseInt(aid) })
    });
    const j = await r.json();
    if (r.ok) {
      const row = document.getElementById('nec-row-' + id);
      if (row) {
        row.innerHTML = `<td colspan="4">
          <span style="color:var(--verde)">✅ <strong>${escHtml(denumireRaw)}</strong> a fost asociat cu succes. Va fi recunoscut la următorul upload.</span>
        </td>`;
      }
      // Actualizeaza badge
      const badge = document.getElementById('badge-nec');
      const cnt = parseInt(badge.textContent||'0') - 1;
      if (cnt > 0) { badge.textContent = cnt; } else { badge.style.display = 'none'; }
    } else {
      alert('Eroare: ' + (j.detail || 'Necunoscut'));
    }
  } catch(e) {
    alert('Eroare rețea: ' + e.message);
  }
}

async function stergeNecunoscuta(id) {
  if (!confirm('Ștergeți această intrare? (Ex: artefact OCR, nu este o analiză reală)')) return;
  try {
    await fetch('/analiza-necunoscuta/' + id, { method: 'DELETE' });
    const row = document.getElementById('nec-row-' + id);
    if (row) row.remove();
    const badge = document.getElementById('badge-nec');
    const cnt = parseInt(badge.textContent||'0') - 1;
    if (cnt > 0) { badge.textContent = cnt; } else { badge.style.display = 'none'; }
  } catch(e) {
    alert('Eroare: ' + e.message);
  }
}

// ─── Util ─────────────────────────────────────────────────────────────────────
function formatDateOnly(s) {
  if (!s) return '';
  const txt = String(s).trim();
  // DD.MM.YYYY (+ optional time)
  let m = txt.match(/(\d{2})[./-](\d{2})[./-](\d{4})/);
  if (m) return `${m[1]}.${m[2]}.${m[3]}`;
  // YYYY-MM-DD / YYYY.MM.DD
  m = txt.match(/(\d{4})[./-](\d{2})[./-](\d{2})/);
  if (m) return `${m[3]}.${m[2]}.${m[1]}`;
  // ISO datetime fallback
  if (txt.includes('T') && txt.length >= 10) {
    const iso = txt.substring(0, 10);
    const p = iso.split('-');
    if (p.length === 3) return `${p[2]}.${p[1]}.${p[0]}`;
    return iso;
  }
  return txt.substring(0, 10);
}

function escHtml(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function afiseazaMesaj(containerId, tip, html) {
  document.getElementById(containerId).innerHTML = `<div class="mesaj ${tip}">${html}</div>`;
}

// La incarcare initiala
incarcaRecenti();
// Verifica daca exista analize necunoscute si actualizeaza badge
(async () => {
  try {
    const r = await fetch('/analize-necunoscute');
    const lista = await r.json();
    const badge = document.getElementById('badge-nec');
    if (lista.length > 0) { badge.textContent = lista.length; badge.style.display = ''; }
  } catch {}
})();
</script>
</body>
</html>"""
    return html


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
