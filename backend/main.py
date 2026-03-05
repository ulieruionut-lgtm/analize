"""FastAPI – Analize medicale PDF. Interfata medic + API REST."""
import json
import os
import re
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm

from backend.auth import create_access_token, decode_token, hash_password, verify_password
from backend.config import settings
from backend.database import (
    create_user as db_create_user,
    delete_buletin,
    delete_pacient,
    delete_rezultat_single,
    delete_user_by_id,
    ensure_default_admin,
    export_backup_data,
    get_all_analize_standard,
    get_all_pacienti,
    get_all_users,
    get_analize_necunoscute,
    get_historicul_analiza,
    get_historicul_analiza_by_cod,
    get_pacient_cu_analize,
    get_rezultate_buletin,
    get_user_by_username,
    insert_buletin,
    insert_rezultat,
    add_rezultat_manual,
    search_pacienti,
    sterge_analiza_necunoscuta,
    update_rezultat,
    update_user_password,
    upsert_pacient,
)
from backend.models import PatientParsed
from backend.normalizer import normalize_rezultate
from backend.parser import parse_full_text
from backend.pdf_processor import extract_text_from_pdf

app = FastAPI(title="Analize medicale PDF", version="1.0.0")

_ERORI_LOG = Path(__file__).resolve().parent.parent / "upload_eroare.txt"
_HTTP_BEARER = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_HTTP_BEARER),
):
    """Dependency: verifica JWT si returneaza user dict. Ridica 401 daca nu e autentificat."""
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Nu esti autentificat. Logheaza-te.")
    payload = decode_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Token invalid sau expirat.")
    return {"username": payload["sub"]}


@app.on_event("startup")
async def startup_event():
    """La pornire: creeaza utilizatorul admin daca nu exista niciun user."""
    try:
        print("[STARTUP] Verificare/Creare utilizator admin...")
        result = ensure_default_admin()
        if result:
            print("[STARTUP] ✓ Utilizator admin creat (username: admin, password: admin123)")
        else:
            print("[STARTUP] ✓ Utilizator admin exista deja")
    except Exception as e:
        print(f"[STARTUP] ✗ Eroare la creare admin: {e}")
        import traceback
        traceback.print_exc()


def _raspuns_eroare(status: int, mesaj: str):
    return JSONResponse(
        status_code=status,
        content={"detail": mesaj[:500]},
        media_type="application/json",
    )


def _normalizare_data_text(raw: str) -> str:
    """Normalizeaza data in format ISO YYYY-MM-DD (compatibil PostgreSQL)."""
    raw = (raw or "").strip()
    raw = raw.replace("/", ".").replace("-", ".")
    # DD.MM.YYYY -> YYYY-MM-DD
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # YYYY.MM.DD -> YYYY-MM-DD
    m = re.match(r"^(\d{4})\.(\d{2})\.(\d{2})$", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
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
        from backend.database import get_cursor
        with get_cursor() as cur:
            cur.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return JSONResponse(content={"status": "error", "database": str(e)}, status_code=503)


@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login cu username si parola. Returneaza JWT token.
    Form: username, password (application/x-www-form-urlencoded)
    """
    user = get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Username sau parola incorecte.")
    token = create_access_token(data={"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer", "username": user["username"]}


@app.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    """Returneaza utilizatorul curent (pentru verificare token)."""
    return current_user


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str


@app.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    """Schimba parola utilizatorului curent."""
    user = get_user_by_username(current_user["username"])
    if not user or not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Parola curenta incorecta.")
    if len(body.new_password.strip()) < 4:
        raise HTTPException(status_code=400, detail="Parola noua trebuie sa aiba minim 4 caractere.")
    ok = update_user_password(current_user["username"], hash_password(body.new_password))
    if not ok:
        raise HTTPException(status_code=500, detail="Nu s-a putut actualiza parola.")
    return {"message": "Parola a fost actualizata."}


def _is_admin(current_user: dict) -> bool:
    return (current_user or {}).get("username", "").lower() == "admin"


@app.get("/users")
async def list_users(current_user: dict = Depends(get_current_user)):
    """Lista utilizatori (doar admin)."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Doar admin poate vedea utilizatorii.")
    return get_all_users()


@app.post("/users")
async def create_user(
    body: CreateUserRequest,
    current_user: dict = Depends(get_current_user),
):
    """Adauga utilizator nou (doar admin)."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Doar admin poate adauga utilizatori.")
    username = (body.username or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username gol.")
    if len((body.password or "").strip()) < 4:
        raise HTTPException(status_code=400, detail="Parola trebuie sa aiba minim 4 caractere.")
    user = db_create_user(username, hash_password(body.password))
    if user is None:
        raise HTTPException(status_code=409, detail=f"Utilizatorul '{username}' exista deja.")
    return {"message": "Utilizator creat.", "user": {"id": user["id"], "username": user["username"]}}


@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Sterge utilizator (doar admin). Nu se poate sterge contul propriu."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Doar admin poate sterge utilizatori.")
    me_user = get_user_by_username(current_user["username"])
    if me_user and me_user.get("id") == user_id:
        raise HTTPException(status_code=400, detail="Nu poti sterge contul tau.")
    if not delete_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="Utilizatorul nu a fost gasit sau nu s-a putut sterge.")
    return {"message": "Utilizator sters."}


@app.get("/api/backup")
async def backup_export(current_user: dict = Depends(get_current_user)):
    """Export backup baza de analize (JSON). Doar admin."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Doar admin poate descarca backup-ul.")
    try:
        data = export_backup_data()
        ts = data.get("exported_at", "")[:19].replace("-", "").replace("T", "_").replace(":", "")
        filename = f"analize_backup_{ts}.json" if ts else "analize_backup_" + datetime.utcnow().strftime("%Y%m%d_%H%M") + ".json"
        body = json.dumps(data, ensure_ascii=False, indent=2)
        return StreamingResponse(
            iter([body.encode("utf-8")]),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Eroare la export: {str(e)}"},
        )


@app.delete("/buletin/{buletin_id}")
async def sterge_buletin(buletin_id: int, current_user: dict = Depends(get_current_user)):
    """Sterge un buletin (cu toate analizele din el)."""
    ok = delete_buletin(buletin_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Buletinul nu a fost găsit.")
    return {"message": "Buletin șters."}


@app.delete("/pacient/{pacient_id}")
async def sterge_pacient(pacient_id: int, current_user: dict = Depends(get_current_user)):
    """Sterge un pacient cu toate buletinele si analizele lui."""
    ok = delete_pacient(pacient_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Pacientul nu a fost găsit.")
    return {"message": "Pacient șters complet."}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Primeste PDF, extrage text (sau OCR), parseaza CNP + nume + analize, salveaza in DB."""
    tmp_path = None
    try:
        if not file or not file.filename or not file.filename.lower().endswith(".pdf"):
            return JSONResponse(status_code=400, content={"detail": "Fisierul trebuie sa fie PDF."})
        content = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        text, tip, ocr_err, colored_tokens = extract_text_from_pdf(tmp_path)
        if not text or len(text.strip()) < 10:
            detail = "Nu s-a putut extrage text din PDF (gol sau prea scurt)."
            if ocr_err:
                detail += " " + str(ocr_err)
            return JSONResponse(status_code=422, content={"detail": detail})
        parsed: Optional[PatientParsed] = parse_full_text(text)
        if not parsed:
            return JSONResponse(status_code=422, content={"detail": "Nu s-a gasit un CNP valid in PDF."})
        normalize_rezultate(parsed.rezultate)
        # Aplica colored_tokens: daca valoarea unui rezultat apare cu culoare non-neagra in PDF
        # si nu are deja un flag, o marcam ca anormala (H implicit = atentie)
        if colored_tokens:
            import re as _re_ct
            for r in parsed.rezultate:
                if r.flag is None and r.valoare is not None:
                    val_str = str(r.valoare).rstrip("0").rstrip(".")
                    val_str_comma = val_str.replace(".", ",")
                    if val_str in colored_tokens or val_str_comma in colored_tokens:
                        # Determina H sau L daca avem interval, altfel H ca semnal
                        if r.interval_min is not None and r.valoare < r.interval_min:
                            r.flag = "L"
                        else:
                            r.flag = "H"
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
async def lista_pacienti(q: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Lista pacienti. Optional: ?q=text pentru cautare dupa CNP sau Nume."""
    if q and q.strip():
        return search_pacienti(q.strip())
    return get_all_pacienti()


@app.get("/pacient/{cnp}/evolutie-matrice")
async def get_pacient_evolutie_matrice(cnp: str, current_user: dict = Depends(get_current_user)):
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
            "id": pacient_data.get("id"),
            "cnp": pacient_data.get("cnp"),
            "nume": pacient_data.get("nume"),
            "prenume": pacient_data.get("prenume")
        },
        "date_buletine": date_buletine,
        "buletine_ids": [b.get("id") for b in buletine_sorted],
        "analize": analize_result
    }


@app.get("/pacient/{cnp}")
async def get_pacient(cnp: str, current_user: dict = Depends(get_current_user)):
    """Pacientul cu CNP dat + toate buletinele + rezultatele."""
    result = get_pacient_cu_analize(cnp)
    if not result:
        raise HTTPException(status_code=404, detail="Pacient negasit.")
    return result


@app.get("/analize-standard")
async def lista_analize_standard(current_user: dict = Depends(get_current_user)):
    """Lista tuturor tipurilor de analize din baza de date."""
    return get_all_analize_standard()


@app.get("/buletin/{buletin_id}/rezultate")
async def get_buletin_rezultate(buletin_id: int, current_user: dict = Depends(get_current_user)):
    """Lista tuturor rezultatelor dintr-un buletin (pentru editare manuala)."""
    rows = get_rezultate_buletin(buletin_id)
    return rows


@app.put("/rezultat/{rezultat_id}")
async def edit_rezultat(rezultat_id: int, body: dict, current_user: dict = Depends(get_current_user)):
    """Editeaza partial un rezultat existent: actualizeaza doar campurile trimise.
    Daca se schimba analiza_standard_id, salveaza denumire_raw ca alias pentru invatare.
    """
    if not body:
        raise HTTPException(status_code=422, detail="Body gol — nimic de actualizat.")
    ok = update_rezultat(rezultat_id=rezultat_id, body=body)
    if not ok:
        raise HTTPException(status_code=404, detail="Rezultatul nu a fost gasit.")

    # Daca s-a schimbat tipul de analiza, inregistreaza denumire_raw ca alias
    alias_salvat = False
    new_std_id = body.get("analiza_standard_id")
    if new_std_id:
        from backend.database import get_cursor, _use_sqlite
        with get_cursor(commit=False) as cur:
            ph = "?" if _use_sqlite() else "%s"
            cur.execute(f"SELECT denumire_raw FROM rezultate_analize WHERE id = {ph}", (rezultat_id,))
            row = cur.fetchone()
            if row:
                denumire = row[0] if _use_sqlite() else row['denumire_raw']
                if denumire and denumire.strip():
                    from backend.normalizer import adauga_alias_nou
                    alias_salvat = adauga_alias_nou(denumire.strip(), int(new_std_id))

    return {"ok": True, "alias_salvat": alias_salvat}


@app.delete("/rezultat/{rezultat_id}")
async def sterge_rezultat(rezultat_id: int, current_user: dict = Depends(get_current_user)):
    """Sterge un singur rezultat dintr-un buletin."""
    ok = delete_rezultat_single(rezultat_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Rezultatul nu a fost gasit.")
    return {"ok": True}


@app.post("/buletin/{buletin_id}/rezultat")
async def adauga_rezultat(buletin_id: int, body: dict, current_user: dict = Depends(get_current_user)):
    """Adauga manual un rezultat intr-un buletin existent.
    Daca se specifica si analiza_standard_id, denumire_raw este salvata ca alias
    pentru a fi recunoscuta automat la upload-uri viitoare.
    """
    valoare = body.get("valoare")
    if valoare is None:
        raise HTTPException(status_code=422, detail="Campul 'valoare' este obligatoriu.")
    denumire = (body.get("denumire_raw") or "").strip()
    if not denumire:
        raise HTTPException(status_code=422, detail="Campul 'denumire_raw' este obligatoriu.")
    analiza_standard_id = body.get("analiza_standard_id")
    row = add_rezultat_manual(
        buletin_id=buletin_id,
        analiza_standard_id=analiza_standard_id,
        denumire_raw=denumire,
        valoare=float(valoare),
        unitate=body.get("unitate"),
        flag=body.get("flag"),
    )
    if not row:
        raise HTTPException(status_code=500, detail="Eroare la adaugarea rezultatului.")

    # Daca s-a specificat tipul de analiza, inregistreaza denumire_raw ca alias
    # pentru a fi recunoscuta automat la upload-uri viitoare
    alias_salvat = False
    if analiza_standard_id and denumire:
        from backend.normalizer import adauga_alias_nou
        alias_salvat = adauga_alias_nou(denumire, int(analiza_standard_id))

    return {"ok": True, "id": row["id"], "alias_salvat": alias_salvat}


@app.get("/analize-necunoscute")
async def lista_necunoscute(toate: bool = False, current_user: dict = Depends(get_current_user)):
    """Analize nerecunoscute de normalizer (neaprobate sau toate)."""
    return get_analize_necunoscute(doar_neaprobate=not toate)


@app.post("/aproba-alias")
async def aproba_alias(body: dict, current_user: dict = Depends(get_current_user)):
    """
    Aprobare alias: asociaza o denumire_raw necunoscuta cu o analiza_standard.
    Body: { "denumire_raw": "...", "analiza_standard_id": 5 }
    """
    raw = (body.get("denumire_raw") or "").strip()
    aid = body.get("analiza_standard_id")
    if not raw or not aid:
        return JSONResponse(status_code=400, content={"detail": "Campuri obligatorii: denumire_raw, analiza_standard_id"})
    from backend.normalizer import adauga_alias_nou
    ok = adauga_alias_nou(raw, int(aid))
    if ok:
        return {"ok": True, "mesaj": f"Alias '{raw}' asociat cu succes."}
    return JSONResponse(status_code=500, content={"detail": "Eroare la salvarea alias-ului."})


@app.delete("/analiza-necunoscuta/{id_nec}")
async def sterge_necunoscuta(id_nec: int, current_user: dict = Depends(get_current_user)):
    """Sterge o analiza necunoscuta (ex: zgomot, artefact OCR)."""
    sterge_analiza_necunoscuta(id_nec)
    return {"ok": True}


@app.get("/analiza-historicul/{analiza_id}")
async def historicul_analiza(analiza_id: int, current_user: dict = Depends(get_current_user)):
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
  .val-H {
    color: var(--rosu);
    font-weight: 700;
    outline: 2px solid var(--rosu);
    outline-offset: 3px;
    border-radius: 3px;
    padding: 1px 5px;
    display: inline-block;
  }
  .val-L {
    color: var(--albastru);
    font-weight: 700;
    outline: 2px solid var(--albastru);
    outline-offset: 3px;
    border-radius: 3px;
    padding: 1px 5px;
    display: inline-block;
  }
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
    max-width: 280px;
    width: 280px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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

  /* Login screen */
  #login-screen {
    max-width: 400px; margin: 80px auto; padding: 40px;
    background: white; border-radius: 12px; box-shadow: var(--shadow);
  }
  #login-screen h2 { font-size: 1.3rem; margin-bottom: 24px; color: var(--gri); }
  .login-field { margin-bottom: 18px; }
  .login-field label { display: block; font-size: 0.9rem; color: var(--gri); margin-bottom: 6px; }
  .login-field input {
    width: 100%; padding: 12px 16px;
    border: 1px solid var(--border); border-radius: 8px;
    font-size: 1rem;
  }
  .login-field input:focus { outline: none; border-color: var(--albastru); box-shadow: 0 0 0 3px rgba(26,115,232,0.15); }
  #login-err { color: var(--rosu); font-size: 0.9rem; margin-top: 12px; display: none; }
  .btn-logout { background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.5); padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
  .btn-logout:hover { background: rgba(255,255,255,0.3); }

  /* Tab-uri dinamice pacienți */
  .tabs-dinamice {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 8px 24px;
    background: #f8f9fa;
    border-bottom: 1px solid var(--border);
  }
  .tab-pacient-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px 5px 12px;
    border-radius: 20px;
    background: white;
    border: 1px solid var(--border);
    cursor: pointer;
    font-size: 0.82rem;
    color: var(--text);
    transition: all 0.15s;
    max-width: 200px;
  }
  .tab-pacient-btn:hover { border-color: var(--albastru); color: var(--albastru); }
  .tab-pacient-btn.activ { background: var(--albastru); color: white; border-color: var(--albastru); }
  .tab-pacient-btn .tab-nume { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 130px; }
  .tab-pacient-btn .close-tab {
    flex-shrink: 0;
    width: 16px; height: 16px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.9rem; line-height: 1;
    opacity: 0.6;
  }
  .tab-pacient-btn .close-tab:hover { opacity: 1; background: rgba(0,0,0,0.15); }
  .tab-pacient-btn.activ .close-tab:hover { background: rgba(255,255,255,0.3); }
  #continut-pacienti-dinamici { max-width: 1100px; margin: 0 auto; padding: 24px; }

  @media (max-width: 600px) {
    .content { padding: 12px; }
    .tabs { overflow-x: auto; }
    .search-row { flex-direction: column; }
    #continut-pacienti-dinamici { padding: 12px; }
    .tabs-dinamice { padding: 8px 12px; }
  }
</style>
</head>
<body>

<!-- LOGIN SCREEN (vizibil cand nu e autentificat) -->
<div id="login-screen" style="display:none">
  <h2>🔐 Logare - Analize Medicale</h2>
  <form id="login-form" onsubmit="return doLogin(event)">
    <div class="login-field">
      <label>Utilizator</label>
      <input type="text" id="login-username" name="username" required placeholder="admin" autocomplete="username">
    </div>
    <div class="login-field">
      <label>Parolă</label>
      <input type="password" id="login-password" name="password" required placeholder="••••••••" autocomplete="current-password">
    </div>
    <button type="submit" class="btn btn-primary" style="width:100%;margin-top:8px">Intră în cont</button>
  </form>
  <div id="login-err"></div>
  <p style="margin-top:20px;font-size:0.8rem;color:var(--gri)">Implicit: admin / admin123 (schimbă după prima logare)</p>
</div>

<!-- MAIN APP (vizibil doar dupa login) -->
<div id="app-container" style="display:none">

<div class="header" style="justify-content:space-between">
  <div>
    <h1>🏥 Analize Medicale</h1>
    <div class="sub">Panou medic – v03.03.2026 | <span id="user-display"></span></div>
  </div>
  <div style="display:flex;gap:8px;align-items:center">
    <button class="btn-logout" id="btn-header-backup" onclick="exportBackup(this)" style="display:none">📥 Export backup</button>
    <button class="btn-logout" onclick="logout()">Ieșire</button>
  </div>
</div>
<div class="tabs">
  <button class="tab-btn activ" onclick="schimbTab('upload')">📤 Upload PDF</button>
  <button class="tab-btn" onclick="schimbTab('pacient')">👤 Pacient</button>
  <button class="tab-btn" onclick="schimbTab('analiza')">📊 Tip Analiză</button>
  <button class="tab-btn" id="tab-btn-alias" onclick="schimbTab('alias')">🔗 Analize necunoscute <span id="badge-nec" style="display:none;background:var(--rosu);color:white;border-radius:10px;padding:1px 7px;font-size:0.75rem;margin-left:4px">0</span></button>
  <button class="tab-btn" onclick="schimbTab('setari')">⚙️ Setări</button>
</div>

<!-- Bara tab-uri dinamice pacienți (apare doar când sunt pacienți deschisi) -->
<div class="tabs-dinamice" id="tabs-dinamice" style="display:none"></div>

<div class="content">

  <!-- TAB 1: Upload -->
  <div id="tab-upload" class="sectiune activa">
    <div class="card">
      <h2>Încarcă buletine PDF</h2>
      <div class="upload-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
        <div class="upload-icon">📄</div>
        <p>Trage fișierele PDF aici sau <strong>click</strong> pentru a selecta</p>
        <p style="font-size:0.8rem;margin-top:6px;color:#9aa0a6">Poți selecta mai multe fișiere deodată · PDF text și scanat (OCR automat)</p>
        <div id="file-name"></div>
      </div>
      <input type="file" id="file-input" accept=".pdf" multiple>
      <div style="margin-top:16px; display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
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

  <!-- TAB 5: Setari -->
  <div id="tab-setari" class="sectiune">
    <div class="card">
      <h2>Schimbare parolă</h2>
      <p style="font-size:0.88rem;color:var(--gri);margin-bottom:12px">Schimbă parola contului tău curent.</p>
      <div class="search-row" style="max-width:400px;flex-direction:column;align-items:stretch;gap:10px">
        <input type="password" class="input-search" id="setari-parola-curenta" placeholder="Parola curentă">
        <input type="password" class="input-search" id="setari-parola-noua" placeholder="Parola nouă (min. 4 caractere)">
        <input type="password" class="input-search" id="setari-parola-confirma" placeholder="Confirmă parola nouă">
        <button class="btn btn-primary" onclick="schimbaParola()">Salvează parola</button>
      </div>
      <p id="setari-msg-parola" style="margin-top:10px;font-size:0.88rem;display:none"></p>
    </div>
    <div class="card" id="card-backup" style="display:none">
      <h2>Backup baza de date</h2>
      <p style="font-size:0.88rem;color:var(--gri);margin-bottom:12px">Descarcă o copie de siguranță a pacienților, buletinelor și rezultatelor (fișier JSON).</p>
      <button class="btn btn-primary" id="btn-export-backup" onclick="exportBackup(this)">Exportă backup</button>
    </div>
    <div class="card" id="card-user-management" style="display:none">
      <h2>Gestionare utilizatori</h2>
      <p style="font-size:0.88rem;color:var(--gri);margin-bottom:12px">Adaugă sau șterge utilizatori. Doar admin.</p>
      <div class="search-row" style="max-width:400px;flex-direction:row;flex-wrap:wrap;gap:8px;margin-bottom:16px">
        <input class="input-search" id="setari-nou-username" placeholder="Username nou" style="flex:1;min-width:120px">
        <input type="password" class="input-search" id="setari-nou-parola" placeholder="Parolă (min. 4)" style="flex:1;min-width:120px">
        <button class="btn btn-secondary" onclick="adaugaUtilizator()">Adaugă utilizator</button>
      </div>
      <p id="setari-msg-users" style="margin-bottom:10px;font-size:0.88rem;display:none"></p>
      <div class="tabel-container">
        <table>
          <thead><tr><th>ID</th><th>Utilizator</th><th>Creat</th><th></th></tr></thead>
          <tbody id="lista-utilizatori"></tbody>
        </table>
      </div>
    </div>
  </div>

</div><!-- /content -->

<!-- Zona continut tab-uri dinamice pacienti -->
<div id="continut-pacienti-dinamici" style="display:none"></div>

<script>
// ─── Tab-uri dinamice pacienti ───────────────────────────────────────────────
const _tabPacienti = {};   // { cnp: { nume, html } }
let _tabPacientActiv = null;

function deschideTabPacient(cnp, nume, htmlContent) {
  const baraDinamica = document.getElementById('tabs-dinamice');
  const continutDinamic = document.getElementById('continut-pacienti-dinamici');

  // Verifica atat in cache cat si in DOM (evita duplicate la stergere/reincarca)
  const btnExistent = document.querySelector('.tab-pacient-btn[data-cnp="' + cnp + '"]');

  if (!_tabPacienti[cnp] && !btnExistent) {
    // Tab nou - nu exista nici in cache, nici in DOM
    _tabPacienti[cnp] = { nume, html: htmlContent };

    const btn = document.createElement('button');
    btn.className = 'tab-pacient-btn';
    btn.setAttribute('data-cnp', cnp);
    btn.innerHTML =
      '<span class="tab-nume">👤 ' + escHtml(nume) + '</span>' +
      '<span class="close-tab" title="Inchide">×</span>';

    btn.querySelector('.close-tab').addEventListener('click', function(e) {
      e.stopPropagation();
      inchideTabPacient(cnp);
    });
    btn.addEventListener('click', function() {
      activeazaTabPacient(cnp);
    });
    baraDinamica.appendChild(btn);
    baraDinamica.style.display = 'flex';
  } else {
    // Tab existent - actualizeaza doar continutul si eventual numele
    if (!_tabPacienti[cnp]) _tabPacienti[cnp] = { nume, html: htmlContent };
    else _tabPacienti[cnp].html = htmlContent;

    // Actualizeaza numele daca e mai bun (nu mai e CNP-ul gol)
    if (nume && nume !== cnp) {
      _tabPacienti[cnp].nume = nume;
      const tabBtn = document.querySelector('.tab-pacient-btn[data-cnp="' + cnp + '"]');
      if (tabBtn) {
        const span = tabBtn.querySelector('.tab-nume');
        if (span) span.textContent = '👤 ' + nume;
      }
    }
  }

  activeazaTabPacient(cnp);
}

function activeazaTabPacient(cnp) {
  const continutDinamic = document.getElementById('continut-pacienti-dinamici');

  // Dezactiveaza tab-urile principale
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('activ'));
  document.querySelectorAll('.sectiune').forEach(s => s.classList.remove('activa'));
  document.getElementById('continut-pacienti-dinamici').style.display = '';

  // Marcheaza tab-ul activ
  document.querySelectorAll('.tab-pacient-btn').forEach(b => b.classList.remove('activ'));
  const btn = document.querySelector('.tab-pacient-btn[data-cnp="' + cnp + '"]');
  if (btn) btn.classList.add('activ');

  // Afiseaza continutul
  continutDinamic.innerHTML = _tabPacienti[cnp]?.html || '';
  _tabPacientActiv = cnp;
}

function inchideTabPacient(cnp) {
  const btn = document.querySelector('.tab-pacient-btn[data-cnp="' + cnp + '"]');
  if (btn) btn.remove();
  delete _tabPacienti[cnp];

  const baraDinamica = document.getElementById('tabs-dinamice');
  const continutDinamic = document.getElementById('continut-pacienti-dinamici');
  const tabRamas = Object.keys(_tabPacienti);

  if (tabRamas.length === 0) {
    baraDinamica.style.display = 'none';
    continutDinamic.style.display = 'none';
    continutDinamic.innerHTML = '';
    _tabPacientActiv = null;
    // Revine la tab-ul Pacient
    schimbTab('pacient');
  } else if (_tabPacientActiv === cnp) {
    // Activeaza ultimul tab ramas
    activeazaTabPacient(tabRamas[tabRamas.length - 1]);
  }
}

// ─── Autentificare ───────────────────────────────────────────────────────────
const AUTH_KEY = 'analize_token';

function getToken() { return localStorage.getItem(AUTH_KEY); }
function setToken(t) { localStorage.setItem(AUTH_KEY, t); }
function clearToken() { localStorage.removeItem(AUTH_KEY); }
function getAuthHeaders() {
  const t = getToken();
  return t ? { 'Authorization': 'Bearer ' + t } : {};
}

async function checkAuth() {
  const token = getToken();
  if (!token) { document.getElementById('login-screen').style.display='block'; return; }
  try {
    const r = await fetch('/me', { headers: getAuthHeaders() });
    if (r.ok) {
      const u = await r.json();
      document.getElementById('login-screen').style.display = 'none';
      document.getElementById('app-container').style.display = 'block';
      document.getElementById('user-display').textContent = 'Logat: ' + (u.username || '');
      const btnBackup = document.getElementById('btn-header-backup');
      if (btnBackup) btnBackup.style.display = (u.username || '').toLowerCase() === 'admin' ? 'inline-block' : 'none';
      return;
    }
  } catch {}
  clearToken();
  document.getElementById('login-screen').style.display = 'block';
  document.getElementById('app-container').style.display = 'none';
}

async function doLogin(ev) {
  ev.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-err');
  errEl.style.display = 'none';
  try {
    const form = new URLSearchParams();
    form.append('username', username);
    form.append('password', password);
    const r = await fetch('/login', { method: 'POST', body: form, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
    const data = await r.json().catch(() => ({}));
    if (r.ok) {
      setToken(data.access_token);
      document.getElementById('login-password').value = '';
      checkAuth();
    } else {
      errEl.textContent = data.detail || 'Eroare la logare';
      errEl.style.display = 'block';
    }
  } catch (e) {
    errEl.textContent = 'Eroare: ' + e.message;
    errEl.style.display = 'block';
  }
  return false;
}

function logout() {
  clearToken();
  document.getElementById('login-screen').style.display = 'block';
  document.getElementById('app-container').style.display = 'none';
}

// ─── Tab Setari ─────────────────────────────────────────────────────────────
async function incarcaSetari() {
  document.getElementById('setari-msg-parola').style.display = 'none';
  document.getElementById('setari-msg-users').style.display = 'none';
  const card = document.getElementById('card-user-management');
  const cardBackup = document.getElementById('card-backup');
  try {
    const r = await fetch('/me', { headers: getAuthHeaders() });
    if (!r.ok) return;
    const u = await r.json();
    if ((u.username || '').toLowerCase() === 'admin') {
      card.style.display = 'block';
      if (cardBackup) cardBackup.style.display = 'block';
      incarcaListaUtilizatori();
    } else {
      card.style.display = 'none';
      if (cardBackup) cardBackup.style.display = 'none';
    }
  } catch { card.style.display = 'none'; if (cardBackup) cardBackup.style.display = 'none'; }
}

async function exportBackup(btnEl) {
  const btns = [
    document.getElementById('btn-export-backup'),
    document.getElementById('btn-header-backup'),
    btnEl || null
  ].filter(Boolean);
  btns.forEach(b => { b.disabled = true; b._txt = b.textContent; b.textContent = 'Se descarcă…'; });
  try {
    const r = await fetch('/api/backup', { headers: getAuthHeaders() });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      alert('Eroare la backup: ' + (j.detail || r.status));
      return;
    }
    const blob = await r.blob();
    const disp = r.headers.get('Content-Disposition');
    let filename = 'analize_backup.json';
    if (disp) {
      const m = disp.match(/filename="?([^";\n]+)"?/);
      if (m) filename = m[1].trim();
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  } catch (e) {
    alert('Eroare: ' + (e.message || ''));
  } finally {
    btns.forEach(b => { b.disabled = false; b.textContent = b._txt || 'Exportă backup'; });
  }
}

async function incarcaListaUtilizatori() {
  const tbody = document.getElementById('lista-utilizatori');
  tbody.innerHTML = '<tr><td colspan="4" style="color:var(--gri)">Se încarcă…</td></tr>';
  try {
    const r = await fetch('/users', { headers: getAuthHeaders() });
    const users = r.ok ? await r.json() : [];
    tbody.innerHTML = '';
    if (!Array.isArray(users) || users.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="color:var(--gri)">Niciun utilizator</td></tr>';
      return;
    }
    users.forEach(u => {
      const d = u.created_at ? (typeof u.created_at === 'string' ? u.created_at.slice(0,10) : '') : '';
      const btn = '<button class="btn btn-secondary" style="padding:4px 8px;font-size:0.8rem" onclick="stergeUtilizator(' + u.id + ')">Șterge</button>';
      tbody.innerHTML += '<tr><td>' + u.id + '</td><td>' + (u.username||'') + '</td><td>' + d + '</td><td>' + btn + '</td></tr>';
    });
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="4" style="color:var(--rosu)">Eroare: ' + (e.message||'') + '</td></tr>';
  }
}

async function schimbaParola() {
  const curr = document.getElementById('setari-parola-curenta').value;
  const noua = document.getElementById('setari-parola-noua').value;
  const conf = document.getElementById('setari-parola-confirma').value;
  const msg = document.getElementById('setari-msg-parola');
  msg.style.display = 'block';
  msg.style.color = 'var(--rosu)';
  if (!curr || !noua || !conf) {
    msg.textContent = 'Completează toate câmpurile.';
    return;
  }
  if (noua.length < 4) {
    msg.textContent = 'Parola nouă trebuie să aibă minim 4 caractere.';
    return;
  }
  if (noua !== conf) {
    msg.textContent = 'Parola nouă și confirmarea nu coincid.';
    return;
  }
  try {
    const r = await fetch('/change-password', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password: curr, new_password: noua })
    });
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      msg.style.color = 'var(--verde)';
      msg.textContent = 'Parola a fost actualizată.';
      document.getElementById('setari-parola-curenta').value = '';
      document.getElementById('setari-parola-noua').value = '';
      document.getElementById('setari-parola-confirma').value = '';
    } else {
      msg.textContent = j.detail || 'Eroare la actualizare.';
    }
  } catch (e) {
    msg.textContent = 'Eroare: ' + (e.message || '');
  }
}

async function adaugaUtilizator() {
  const username = document.getElementById('setari-nou-username').value.trim();
  const parola = document.getElementById('setari-nou-parola').value;
  const msg = document.getElementById('setari-msg-users');
  msg.style.display = 'block';
  msg.style.color = 'var(--rosu)';
  if (!username) {
    msg.textContent = 'Introdu username-ul.';
    return;
  }
  if ((parola || '').length < 4) {
    msg.textContent = 'Parola trebuie să aibă minim 4 caractere.';
    return;
  }
  try {
    const r = await fetch('/users', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password: parola })
    });
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      msg.style.color = 'var(--verde)';
      msg.textContent = 'Utilizator adăugat.';
      document.getElementById('setari-nou-username').value = '';
      document.getElementById('setari-nou-parola').value = '';
      incarcaListaUtilizatori();
    } else {
      msg.textContent = j.detail || 'Eroare la adăugare.';
    }
  } catch (e) {
    msg.textContent = 'Eroare: ' + (e.message || '');
  }
}

async function stergeUtilizator(id) {
  if (!confirm('Ștergi acest utilizator?')) return;
  try {
    const r = await fetch('/users/' + id, { method: 'DELETE', headers: getAuthHeaders() });
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      incarcaListaUtilizatori();
      document.getElementById('setari-msg-users').style.display = 'block';
      document.getElementById('setari-msg-users').style.color = 'var(--verde)';
      document.getElementById('setari-msg-users').textContent = 'Utilizator șters.';
    } else {
      document.getElementById('setari-msg-users').style.display = 'block';
      document.getElementById('setari-msg-users').style.color = 'var(--rosu)';
      document.getElementById('setari-msg-users').textContent = j.detail || 'Eroare la ștergere.';
    }
  } catch (e) {
    document.getElementById('setari-msg-users').style.display = 'block';
    document.getElementById('setari-msg-users').style.color = 'var(--rosu)';
    document.getElementById('setari-msg-users').textContent = 'Eroare: ' + (e.message || '');
  }
}

// La incarcare: verifica auth
(async function initAuth() {
  await checkAuth();
})();

// ─── Navigare tab-uri ─────────────────────────────────────────────────────────
function schimbTab(id) {
  document.querySelectorAll('.tab-btn').forEach((b,i) => b.classList.toggle('activ', ['upload','pacient','analiza','alias','setari'][i] === id));
  document.querySelectorAll('.sectiune').forEach(s => s.classList.remove('activa'));
  document.getElementById('tab-' + id).classList.add('activa');
  // Ascunde zona dinamica si dezactiveaza tab-urile de pacienti
  document.getElementById('continut-pacienti-dinamici').style.display = 'none';
  document.querySelectorAll('.tab-pacient-btn').forEach(b => b.classList.remove('activ'));
  _tabPacientActiv = null;
  if (id === 'pacient') incarcaListaPacienti('');
  if (id === 'alias') incarcaNecunoscute();
  if (id === 'setari') incarcaSetari();
}

// ─── Upload ──────────────────────────────────────────────────────────────────
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
let fisierSelectat = [];

fileInput.onchange = e => selecteazaFisiere(Array.from(e.target.files));

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  selecteazaFisiere(Array.from(e.dataTransfer.files));
});

function selecteazaFisiere(files) {
  if (!files || !files.length) return;
  const pdfs = files.filter(f => f.name.toLowerCase().endsWith('.pdf'));
  const nonPdf = files.length - pdfs.length;
  if (!pdfs.length) {
    afiseazaMesaj('upload-out','eroare','Fișierele trebuie să fie PDF.');
    return;
  }
  fisierSelectat = pdfs;
  const totalKB = pdfs.reduce((s, f) => s + f.size, 0) / 1024;
  let info = pdfs.length === 1
    ? '📎 ' + pdfs[0].name + ' (' + (pdfs[0].size/1024).toFixed(1) + ' KB)'
    : '📎 ' + pdfs.length + ' fișiere selectate (' + totalKB.toFixed(1) + ' KB total)';
  if (nonPdf > 0) info += ' · <span style="color:var(--rosu)">' + nonPdf + ' ignorate (nu sunt PDF)</span>';
  document.getElementById('file-name').innerHTML = info;
  document.getElementById('btn-upload').disabled = false;
  document.getElementById('btn-text').textContent = pdfs.length === 1 ? 'Procesează PDF' : 'Procesează ' + pdfs.length + ' PDF-uri';
  document.getElementById('upload-out').innerHTML = '';
}

async function trimite() {
  if (!fisierSelectat.length) return;
  const btn = document.getElementById('btn-upload');
  const btnText = document.getElementById('btn-text');
  const prog = document.getElementById('prog');
  btn.disabled = true;
  const out = document.getElementById('upload-out');
  out.innerHTML = '';

  const total = fisierSelectat.length;
  let reusit = 0, esuat = 0;
  const rezultate = [];

  for (let i = 0; i < total; i++) {
    const f = fisierSelectat[i];
    btnText.innerHTML = '<span class="spinner"></span> ' + (i+1) + ' / ' + total + '…';
    prog.textContent = f.size > 500000 ? f.name + ' – fișier mare, OCR poate dura 30-60 sec…' : f.name;

    const fd = new FormData();
    fd.append('file', f);
    let status = 'ok', mesaj = '', pacientInfo = null;
    try {
      const r = await fetch('/upload', { method: 'POST', body: fd, headers: getAuthHeaders() });
      const txt = await r.text();
      let j;
      try { j = JSON.parse(txt); } catch {
        // Serverul a returnat non-JSON (ex: 503 la restart) - reincercam o data
        if (r.status === 503 || r.status === 502 || r.status === 504) {
          j = { detail: 'Serverul se restartează (eroare ' + r.status + '). Încearcă din nou în 10-20 secunde.' };
        } else {
          j = { detail: 'Răspuns neașteptat de la server (status ' + r.status + '). Încearcă din nou.' };
        }
      }
      if (r.ok) {
        reusit++;
        pacientInfo = j.pacient || {};
        mesaj = 'Pacient: <strong>' + escHtml(pacientInfo.nume||'') + '</strong>'
          + ' (CNP: ' + escHtml(pacientInfo.cnp||'') + ')'
          + ' · ' + (j.tip_extragere==='ocr'?'🔍 OCR':'📝 text')
          + ' · <strong>' + (j.numar_analize||0) + ' analize</strong>';
      } else {
        esuat++;
        status = 'err';
        mesaj = (j && j.detail) ? (Array.isArray(j.detail) ? j.detail.join(' ') : j.detail) : 'Eroare ' + r.status;
      }
    } catch(err) {
      esuat++;
      status = 'err';
      mesaj = 'Eroare rețea: ' + err.message + '. Verifică conexiunea și încearcă din nou.';
    }
    rezultate.push({ nume: f.name, status, mesaj, pacientInfo });

    // Afișează progresul live
    out.innerHTML = rezultate.map(rz =>
      '<div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid var(--border)">' +
        '<span style="font-size:1.1rem">' + (rz.status==='ok' ? '✅' : '❌') + '</span>' +
        '<div style="flex:1;min-width:0">' +
          '<div style="font-weight:500;font-size:0.88rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="' + escHtml(rz.nume) + '">' + escHtml(rz.nume) + '</div>' +
          '<div style="font-size:0.82rem;color:' + (rz.status==='ok'?'var(--verde)':'var(--rosu)') + '">' + rz.mesaj + '</div>' +
        '</div>' +
        (rz.status==='ok' && rz.pacientInfo ? '<button class="btn btn-secondary" style="padding:4px 10px;font-size:0.78rem;white-space:nowrap" onclick="veziPacient(\'' + escHtml(rz.pacientInfo.cnp||'') + '\')">👤 Vezi</button>' : '') +
      '</div>'
    ).join('') +
    (i < total-1 ? '<div style="padding:8px 0;color:var(--gri);font-size:0.83rem">Se procesează fișierul ' + (i+2) + '/' + total + '…</div>' : '');
  }

  // Sumar final
  const sumar = total === 1
    ? (reusit ? '<span style="color:var(--verde)">✅ PDF procesat cu succes.</span>' : '<span style="color:var(--rosu)">❌ Procesare eșuată.</span>')
    : '<strong>' + reusit + '/' + total + ' PDF-uri procesate cu succes' + (esuat ? ' · ' + esuat + ' erori' : '') + '</strong>';
  out.insertAdjacentHTML('afterbegin', '<div style="padding:10px 0 12px;font-size:0.9rem">' + sumar + '</div>');

  incarcaRecenti();
  btn.disabled = false;
  btnText.textContent = total === 1 ? 'Procesează PDF' : 'Procesează ' + total + ' PDF-uri';
  prog.textContent = '';
  fisierSelectat = [];
  document.getElementById('file-name').innerHTML = '';
  fileInput.value = '';
}

async function incarcaRecenti() {
  try {
    const r = await fetch('/pacienti', { headers: getAuthHeaders() });
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
    const r = await fetch(url, { headers: getAuthHeaders() });
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
  // Daca tab-ul pacientului e deja deschis, doar il activeaza
  if (_tabPacienti[cnp]) {
    activeazaTabPacient(cnp);
    return;
  }

  // Arata placeholder in tab dinamic temporar
  const numeTemporar = cnp;
  deschideTabPacient(cnp, numeTemporar,
    '<div class="card"><p style="color:var(--gri)">Se încarcă datele pacientului…</p></div>');

  try {
    const r = await fetch('/pacient/' + encodeURIComponent(cnp) + '/evolutie-matrice', { headers: getAuthHeaders() });
    if (!r.ok) {
      deschideTabPacient(cnp, cnp,
        '<div class="card"><p style="color:red">Pacientul nu a fost găsit.</p></div>');
      return;
    }

    const data = await r.json();
    const numePacient = (data.pacient.nume||'') + (data.pacient.prenume ? ' ' + data.pacient.prenume : '');
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
        <div style="margin-left:auto">
          <button class="btn" style="background:var(--rosu);color:white;padding:8px 16px;font-size:0.82rem"
            onclick="stergePacient(${data.pacient.id},'${escHtml(data.pacient.nume||'')}','${escHtml(cnp)}')">
            🗑️ Șterge pacient
          </button>
        </div>
      </div>`;

    if (!data.analize.length) {
      html += '<p style="color:var(--gri);padding:20px;text-align:center">Nicio analiză găsită pentru acest pacient.</p></div>';
      deschideTabPacient(cnp, numePacient, html);
      return;
    }

    // Tabel evoluție
    html += '<div class="tabel-evolutie-container"><table class="tabel-evolutie">';

    // Header cu date + butoane editare/stergere buletin
    html += '<thead><tr><th class="col-analiza">Tip Analize / Data</th>';
    data.date_buletine.forEach((d, i) => {
      const bId = data.buletine_ids ? data.buletine_ids[i] : null;
      const editBtn = bId ? `<button onclick="editBuletin(${bId},'${escHtml(cnp)}')" title="Editeaza analizele din acest buletin" style="background:none;border:none;cursor:pointer;color:var(--albastru);font-size:0.75rem;padding:2px 4px">✏️ editează</button>` : '';
      const delBtn = bId ? `<button onclick="stergeBuletin(${bId},'${escHtml(cnp)}')" title="Sterge acest buletin" style="background:none;border:none;cursor:pointer;color:var(--rosu);font-size:0.75rem;padding:2px 4px">🗑️ șterge</button>` : '';
      html += `<th style="white-space:nowrap">${escHtml(d)}<br><span style="display:flex;gap:4px;justify-content:center">${editBtn}${delBtn}</span></th>`;
    });
    html += '</tr></thead><tbody>';

    // Rânduri analize
    data.analize.forEach(a => {
      const titleComplet = a.denumire_standard + (a.unitate ? ' (' + a.unitate + ')' : '');
      html += `<tr><td class="col-analiza" title="${escHtml(titleComplet)}">`;
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
          if (flag === 'H' || flag === 'L') {
            const cls = flag === 'H' ? 'val-H' : 'val-L';
            html += `<td style="text-align:center"><span class="${cls}">${escHtml(String(v))}</span></td>`;
          } else {
            html += `<td class="val-ok">${escHtml(String(v))}</td>`;
          }
        }
      });
      html += '</tr>';
    });

    html += '</tbody></table></div></div>';
    deschideTabPacient(cnp, numePacient, html);

    // Actualizeaza numele tab-ului cu numele real
    const tabBtn = document.querySelector('.tab-pacient-btn[data-cnp="' + cnp + '"]');
    if (tabBtn) {
      tabBtn.querySelector('.tab-nume').textContent = '👤 ' + (data.pacient.nume||cnp);
    }

  } catch(e) {
    deschideTabPacient(cnp, cnp,
      '<div class="card"><p style="color:red">Eroare: ' + escHtml(e.message) + '</p></div>');
  }
}

function toggleBuletin(id) {
  const el = document.getElementById('buletin-' + id);
  if (el) el.classList.toggle('deschis');
}

async function stergeBuletin(buletinId, cnp) {
  if (!confirm('Ștergi acest buletin cu TOATE analizele din el? Acțiunea nu poate fi anulată!')) return;
  try {
    const r = await fetch('/buletin/' + buletinId, { method: 'DELETE', headers: getAuthHeaders() });
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      delete _tabPacienti[cnp];
      await veziPacient(cnp);
    } else {
      alert('Eroare: ' + (j.detail || 'Nu s-a putut șterge buletinul.'));
    }
  } catch(e) {
    alert('Eroare: ' + e.message);
  }
}

// ======= EDITARE BULETIN =======
let _editBuletinId = null;
let _editCnp = null;
let _analizeLista = [];

async function editBuletin(buletinId, cnp) {
  _editBuletinId = buletinId;
  _editCnp = cnp;

  // Incarca lista analize standard (pentru dropdown)
  if (!_analizeLista.length) {
    const r = await fetch('/analize-standard', { headers: getAuthHeaders() });
    _analizeLista = r.ok ? await r.json() : [];
  }

  // Incarca rezultatele buletinului
  const r = await fetch('/buletin/' + buletinId + '/rezultate', { headers: getAuthHeaders() });
  if (!r.ok) { alert('Nu s-au putut încărca datele buletinului.'); return; }
  const rezultate = await r.json();

  // Construieste dropdown analize
  let opts = '<option value="">— fara mapare —</option>';
  _analizeLista.forEach(a => {
    opts += `<option value="${a.id}">${escHtml(a.denumire_standard)} (${escHtml(a.cod_standard||'')})</option>`;
  });

  // Construieste tabel rezultate
  let rows = '';
  rezultate.forEach(rz => {
    const selOpts = opts.replace(`value="${rz.analiza_standard_id}"`, `value="${rz.analiza_standard_id}" selected`);
    rows += `<tr id="erow-${rz.id}">
      <td style="min-width:200px">
        <select style="width:100%;font-size:0.8rem;padding:3px" onchange="editField(${rz.id},'analiza_standard_id',this.value||null)">
          ${selOpts}
        </select>
        <div style="font-size:0.72rem;color:var(--gri);margin-top:2px">${escHtml(rz.denumire_raw||'')}</div>
      </td>
      <td><input type="number" step="any" value="${rz.valoare??''}" style="width:80px;padding:3px;font-size:0.85rem"
          onchange="editField(${rz.id},'valoare',parseFloat(this.value)||null)" /></td>
      <td><input type="text" value="${escHtml(rz.unitate||'')}" style="width:60px;padding:3px;font-size:0.85rem"
          onchange="editField(${rz.id},'unitate',this.value)" /></td>
      <td>
        <select style="width:55px;padding:3px;font-size:0.85rem" onchange="editField(${rz.id},'flag',this.value||null)">
          <option value="" ${!rz.flag?'selected':''}>—</option>
          <option value="H" ${rz.flag==='H'?'selected':''}>H</option>
          <option value="L" ${rz.flag==='L'?'selected':''}>L</option>
        </select>
      </td>
      <td>
        <button onclick="stergeRezultat(${rz.id})" style="background:var(--rosu);color:white;border:none;border-radius:4px;padding:3px 8px;cursor:pointer;font-size:0.8rem">✕</button>
      </td>
    </tr>`;
  });

  // Modal
  let modal = document.getElementById('modal-edit-buletin');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'modal-edit-buletin';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:1000;display:flex;align-items:flex-start;justify-content:center;padding-top:40px;overflow-y:auto';
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div style="background:white;border-radius:12px;padding:24px;width:min(900px,96vw);max-height:82vh;overflow-y:auto;box-shadow:0 8px 40px rgba(0,0,0,0.25)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">✏️ Editare buletin #${buletinId}</h3>
        <button onclick="inchideModalEdit()" style="background:none;border:none;font-size:1.5rem;cursor:pointer;color:var(--gri)">✕</button>
      </div>
      <div id="edit-msg" style="margin-bottom:8px;min-height:20px"></div>
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:0.85rem">
          <thead><tr style="background:var(--fundal)">
            <th style="padding:8px;text-align:left;border-bottom:2px solid var(--border)">Analiză</th>
            <th style="padding:8px;border-bottom:2px solid var(--border)">Valoare</th>
            <th style="padding:8px;border-bottom:2px solid var(--border)">Unitate</th>
            <th style="padding:8px;border-bottom:2px solid var(--border)">Flag</th>
            <th style="padding:8px;border-bottom:2px solid var(--border)"></th>
          </tr></thead>
          <tbody id="edit-tbody">${rows}</tbody>
        </table>
      </div>
      <div style="margin-top:20px;padding-top:16px;border-top:1px solid var(--border)">
        <strong style="font-size:0.9rem">➕ Adaugă analiză lipsă</strong>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;align-items:flex-end">
          <div style="position:relative">
            <div style="font-size:0.75rem;color:var(--gri);margin-bottom:3px">Tip analiză <span style="color:#aaa">(caută după nume sau cod)</span></div>
            <input type="text" id="new-analiza-search"
              placeholder="🔍 ex: Hemoglobina, TSH, ALT..."
              autocomplete="off"
              style="padding:6px 10px;font-size:0.85rem;min-width:260px;border:1.5px solid #ccc;border-radius:6px;outline:none"
              oninput="filtreazaAnalizeSearch(this.value)"
              onfocus="filtreazaAnalizeSearch(this.value)"
              onblur="setTimeout(()=>ascundeAnalizeSearch(),200)"
            />
            <input type="hidden" id="new-analiza-id" value="" />
            <div id="new-analiza-dropdown"
              style="display:none;position:absolute;top:100%;left:0;z-index:2000;background:white;border:1.5px solid #ccc;border-radius:6px;box-shadow:0 4px 16px rgba(0,0,0,0.15);max-height:220px;overflow-y:auto;min-width:300px">
            </div>
          </div>
          <div>
            <div style="font-size:0.75rem;color:var(--gri);margin-bottom:3px">Valoare *</div>
            <input type="number" step="any" id="new-valoare" placeholder="ex: 15.9" style="padding:6px;width:90px;font-size:0.85rem;border:1.5px solid #ccc;border-radius:6px" />
          </div>
          <div>
            <div style="font-size:0.75rem;color:var(--gri);margin-bottom:3px">Unitate</div>
            <input type="text" id="new-unitate" placeholder="ex: g/dL" style="padding:6px;width:80px;font-size:0.85rem;border:1.5px solid #ccc;border-radius:6px" />
          </div>
          <div>
            <div style="font-size:0.75rem;color:var(--gri);margin-bottom:3px">Flag</div>
            <select id="new-flag" style="padding:6px;font-size:0.85rem;border:1.5px solid #ccc;border-radius:6px">
              <option value="">—</option>
              <option value="H">H (Ridicat)</option>
              <option value="L">L (Scăzut)</option>
            </select>
          </div>
          <button id="btn-adauga-rez" onclick="adaugaRezultatNou()" style="background:var(--verde);color:white;border:none;border-radius:6px;padding:7px 16px;cursor:pointer;font-size:0.85rem;font-weight:600">➕ Adaugă în buletin</button>
        </div>
        <div id="edit-msg-add" style="margin-top:10px;padding:8px 12px;border-radius:6px;display:none;font-size:0.9rem"></div>
        <div style="margin-top:6px;font-size:0.78rem;color:#888">⚠️ Apasă <strong>➕ Adaugă în buletin</strong> pentru fiecare analiză nouă, înainte de a da Gata.</div>
      </div>
      <div style="margin-top:20px;text-align:right">
        <button onclick="inchideModalEditSiReincarca()" style="background:var(--albastru);color:white;border:none;border-radius:6px;padding:10px 24px;cursor:pointer;font-size:0.9rem;font-weight:600">✅ Gata — Închide</button>
      </div>
    </div>`;
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
}

let _editPending = {};  // { rezultat_id: {field: value} }

function editField(rzId, field, value) {
  if (!_editPending[rzId]) _editPending[rzId] = {};
  _editPending[rzId][field] = value;
  // Salveaza automat dupa 600ms (debounce)
  clearTimeout(_editPending[rzId]._timer);
  _editPending[rzId]._timer = setTimeout(() => saveRezultat(rzId), 600);
}

async function saveRezultat(rzId) {
  const changes = _editPending[rzId];
  if (!changes) return;
  const {_timer, ...body} = changes;
  if (Object.keys(body).length === 0) { delete _editPending[rzId]; return; }
  const row = document.getElementById('erow-' + rzId);
  try {
    const r = await fetch('/rezultat/' + rzId, {
      method: 'PUT',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (r.ok) {
      if (row) {
        row.style.background = '#e8f5e9';
        setTimeout(() => { if(row) row.style.background = ''; }, 1200);
      }
      delete _editPending[rzId];
    } else {
      const j = await r.json().catch(() => ({}));
      showEditMsg('❌ Eroare salvare: ' + (j.detail || r.status), true);
      if (row) { row.style.background = '#fdecea'; setTimeout(() => { if(row) row.style.background = ''; }, 2000); }
    }
  } catch(e) {
    showEditMsg('❌ Eroare rețea: ' + e.message, true);
    if (row) { row.style.background = '#fdecea'; setTimeout(() => { if(row) row.style.background = ''; }, 2000); }
  }
}

async function stergeRezultat(rzId) {
  if (!confirm('Ștergi această analiză din buletin?')) return;
  const r = await fetch('/rezultat/' + rzId, { method: 'DELETE', headers: getAuthHeaders() });
  if (r.ok) {
    const row = document.getElementById('erow-' + rzId);
    if (row) row.remove();
    showEditMsg('Analiză ștearsă.', false);
  } else {
    showEditMsg('Eroare la ștergere.', true);
  }
}

async function adaugaRezultatNou() {
  const aid = document.getElementById('new-analiza-id').value;
  const val = document.getElementById('new-valoare').value.trim();
  const unit = document.getElementById('new-unitate').value.trim();
  const flag = document.getElementById('new-flag').value;

  if (!val) {
    showAddMsg('⚠️ Introduceți valoarea numerică (ex: 15.9)!', true);
    document.getElementById('new-valoare').focus();
    return;
  }
  if (!aid) {
    showAddMsg('⚠️ Selectați tipul de analiză din lista de mai sus!', true);
    return;
  }

  const btn = document.getElementById('btn-adauga-rez');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Se salvează...'; }

  try {
    const analiza = _analizeLista.find(a => String(a.id) === String(aid));
    const denumire = analiza ? analiza.denumire_standard : (unit || 'Analiză adăugată manual');

    const body = {
      analiza_standard_id: parseInt(aid),
      denumire_raw: denumire,
      valoare: parseFloat(val.replace(',', '.')),
      unitate: unit || null,
      flag: flag || null,
    };

    const r = await fetch('/buletin/' + _editBuletinId + '/rezultat', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const j = await r.json().catch(() => ({}));

    if (r.ok) {
      const invatMsg = j.alias_salvat
        ? ' Sistemul a învățat-o și o va recunoaște automat la upload-uri viitoare.'
        : '';
      showAddMsg('✅ ' + escHtml(denumire) + ' (' + val + ' ' + (unit||'') + ') adăugat cu succes!' + invatMsg, false);
      document.getElementById('new-valoare').value = '';
      document.getElementById('new-unitate').value = '';
      document.getElementById('new-flag').value = '';
      document.getElementById('new-analiza-id').value = '';
      const srch = document.getElementById('new-analiza-search');
      if (srch) { srch.value = ''; srch.style.borderColor = '#ccc'; }
    } else {
      showAddMsg('❌ Eroare: ' + (j.detail || 'Nu s-a putut salva. Verifică că ești autentificat.'), true);
    }
  } catch(e) {
    showAddMsg('❌ Eroare rețea: ' + e.message, true);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '➕ Adaugă'; }
  }
}

function showAddMsg(msg, isErr) {
  // Mesaj langa butonul de adaugare (vizibil fara scroll)
  const el = document.getElementById('edit-msg-add');
  if (el) {
    el.textContent = msg;
    el.style.display = 'block';
    el.style.background = isErr ? '#fdecea' : '#e8f5e9';
    el.style.color = isErr ? '#c62828' : '#2e7d32';
    el.style.border = '1px solid ' + (isErr ? '#ef9a9a' : '#a5d6a7');
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    // Auto-ascunde dupa 6 secunde daca e succes
    if (!isErr) setTimeout(() => { el.style.display = 'none'; }, 6000);
  }
}

function showEditMsg(msg, isErr) {
  const el = document.getElementById('edit-msg');
  if (el) {
    el.textContent = msg;
    el.style.color = isErr ? 'var(--rosu)' : 'var(--verde)';
  }
}

function filtreazaAnalizeSearch(query) {
  const dropdown = document.getElementById('new-analiza-dropdown');
  if (!dropdown) return;
  const q = query.trim().toLowerCase();
  const lista = _analizeLista || [];

  const filtrate = q.length === 0
    ? lista.slice(0, 40)  // primele 40 cand e gol
    : lista.filter(a => {
        const den = (a.denumire_standard || '').toLowerCase();
        const cod = (a.cod_standard || '').toLowerCase();
        return den.includes(q) || cod.includes(q);
      }).slice(0, 50);

  if (filtrate.length === 0) {
    dropdown.innerHTML = '<div style="padding:10px;color:#999;font-size:0.85rem">Niciun rezultat</div>';
  } else {
    dropdown.innerHTML = filtrate.map(a => {
      const den = escHtml(a.denumire_standard || '');
      const cod = escHtml(a.cod_standard || '');
      const qEsc = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const highlight = q ? den.replace(new RegExp(qEsc, 'gi'),
        m => '<mark style="background:#fff176;padding:0">' + m + '</mark>'
      ) : den;
      return '<div' +
        ' data-id="' + a.id + '" data-den="' + den + '" data-cod="' + cod + '"' +
        ' style="padding:8px 12px;cursor:pointer;font-size:0.85rem;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;align-items:center"' +
        ' onmousedown="selecteazaAnaliza(this.dataset.id, this.dataset.den, this.dataset.cod)"' +
        ' onmouseover="this.style.background=\'#e3f2fd\'"' +
        ' onmouseout="this.style.background=\'\'"' +
        '><span>' + highlight + '</span><span style="color:#999;font-size:0.75rem;margin-left:8px">' + cod + '</span></div>';
    }).join('');
  }
  dropdown.style.display = 'block';
}

function selecteazaAnaliza(id, denumire, cod) {
  const searchEl = document.getElementById('new-analiza-search');
  const hiddenEl = document.getElementById('new-analiza-id');
  const dropdown = document.getElementById('new-analiza-dropdown');
  if (searchEl) {
    searchEl.value = denumire + (cod ? ' (' + cod + ')' : '');
    searchEl.style.borderColor = 'var(--verde)';
  }
  if (hiddenEl) hiddenEl.value = id;
  if (dropdown) dropdown.style.display = 'none';
  // Focus pe valoare
  const valEl = document.getElementById('new-valoare');
  if (valEl) valEl.focus();
}

function ascundeAnalizeSearch() {
  const dropdown = document.getElementById('new-analiza-dropdown');
  if (dropdown) dropdown.style.display = 'none';
}

function inchideModalEdit() {
  const modal = document.getElementById('modal-edit-buletin');
  if (modal) modal.style.display = 'none';
  document.body.style.overflow = '';
  _editPending = {};
}

async function inchideModalEditSiReincarca() {
  // Verifica daca formularul de adaugare are date nesalvate
  const newVal = (document.getElementById('new-valoare') || {}).value || '';
  const newAid = (document.getElementById('new-analiza-id') || {}).value || '';
  if (newVal.trim()) {
    if (newAid) {
      // Salveaza automat analiza din formular
      await adaugaRezultatNou();
      // Asteapta putin sa se proceseze
      await new Promise(res => setTimeout(res, 400));
    } else {
      // Are valoare dar nu are tip selectat
      showAddMsg('⚠️ Ai introdus o valoare dar nu ai selectat tipul de analiză! Caută și selectează tipul din lista de mai sus.', true);
      const srch = document.getElementById('new-analiza-search');
      if (srch) srch.focus();
      return; // Nu inchide modalul
    }
  }

  // Salveaza orice modificari nesalvate din tabel
  for (const rzId of Object.keys(_editPending)) {
    await saveRezultat(parseInt(rzId));
  }
  inchideModalEdit();
  // Reincarca vizualizarea pacientului
  if (_editCnp) {
    delete _tabPacienti[_editCnp];
    await veziPacient(_editCnp);
  }
}

async function stergePacient(pacientId, numePacient, cnp) {
  if (!confirm('Ștergi pacientul "' + numePacient + '" cu TOATE buletinele și analizele lui? Acțiunea nu poate fi anulată!')) return;
  try {
    const r = await fetch('/pacient/' + pacientId, { method: 'DELETE', headers: getAuthHeaders() });
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      inchideTabPacient(cnp);
      incarcaListaPacienti('');
    } else {
      alert('Eroare: ' + (j.detail || 'Nu s-a putut șterge pacientul.'));
    }
  } catch(e) {
    alert('Eroare: ' + e.message);
  }
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
    const r = await fetch('/pacienti?q=' + encodeURIComponent(q.trim()), { headers: getAuthHeaders() });
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
    const r = await fetch('/pacient/' + encodeURIComponent(cnp), { headers: getAuthHeaders() });
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
    const r = await fetch('/analize-standard', { headers: getAuthHeaders() });
    _analize_std_cache = await r.json();
  } catch { _analize_std_cache = []; }
  return _analize_std_cache;
}

async function incarcaNecunoscute() {
  const el = document.getElementById('lista-necunoscute');
  el.innerHTML = '<p style="color:var(--gri)">Se încarcă…</p>';
  try {
    const [nec, std] = await Promise.all([
      fetch('/analize-necunoscute', { headers: getAuthHeaders() }).then(r => r.json()),
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
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ denumire_raw: denumireRaw, analiza_standard_id: parseInt(aid) })
    });
    const j = await r.json();
    if (r.ok) {
      const row = document.getElementById('nec-row-' + id);
      if (row) {
        row.innerHTML = `<td colspan="4">
          <span style="color:var(--verde)">✅ <strong>${escHtml(denumireRaw)}</strong> a fost asociat cu succes. Toate rezultatele existente au fost actualizate și va fi recunoscut automat la orice upload viitor.</span>
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
    await fetch('/analiza-necunoscuta/' + id, { method: 'DELETE', headers: getAuthHeaders() });
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
    const r = await fetch('/analize-necunoscute', { headers: getAuthHeaders() });
    const lista = await r.json();
    const badge = document.getElementById('badge-nec');
    if (lista.length > 0) { badge.textContent = lista.length; badge.style.display = ''; }
  } catch {}
})();
</script>

</div><!-- /app-container -->
</body>
</html>"""
    return html


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
