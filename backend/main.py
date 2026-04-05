"""FastAPI – Analize medicale PDF. Interfata medic + API REST."""
import asyncio
import io
import json
import os
import re
import tempfile
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from starlette.datastructures import Headers

from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm

from backend.auth import create_access_token, decode_token, hash_password, verify_password
from backend.config import settings
from backend.database import (
    _row_get,
    get_laboratoare,
    get_laborator_analize,
    create_user as db_create_user,
    delete_buletin,
    delete_pacient,
    delete_rezultat_single,
    delete_user_by_id,
    ensure_default_admin,
    export_backup_data,
    restore_from_backup,
    get_all_analize_standard,
    get_pacienti_paginat,
    get_all_users,
    get_analize_necunoscute,
    get_necunoscute_by_ids,
    get_historicul_analiza,
    get_historicul_analiza_by_cod,
    get_pacient_cu_analize,
    get_rezultate_buletin,
    get_user_by_username,
    insert_buletin,
    insert_rezultat,
    rezultat_meta_pentru_insert,
    add_rezultat_manual,
    adauga_analiza_standard,
    backfill_categorie_necunoscuta_din_rezultate,
    sterge_analiza_necunoscuta,
    goleste_analize_asociate,
    update_rezultat,
    update_user_password,
    update_pacient_nume,
    upsert_pacient,
    upload_async_job_get_db,
    upload_async_job_merge_db,
    upload_async_jobs_prune_db,
    upload_async_jobs_use_database,
)
from backend.models import (
    PatientParsed,
    AdaugaAnalizaStdBody,
    AdaugaRezultatBody,
    AprobaAliasBody,
    AprobaAliasBulkBody,
    ActualizeazaPacientBody,
)
from backend.normalizer import normalize_rezultate

app = FastAPI(title="Analize medicale PDF", version="1.0.0")


def _postgresql_connect(url: str):
    """PostgreSQL cu timeout fix — fără connect implicit care poate bloca minute în thread-ul de startup."""
    import psycopg2

    return psycopg2.connect(url, connect_timeout=25)

_ERORI_LOG = Path(__file__).resolve().parent.parent / "upload_eroare.txt"
_HTTP_BEARER = HTTPBearer(auto_error=False)
_ALLOWED_PDF_MIME = {"application/pdf", "application/x-pdf", "application/octet-stream"}
_UPLOAD_ASYNC_JOBS: dict[str, dict] = {}
_UPLOAD_ASYNC_LOCK = threading.Lock()
_UPLOAD_ASYNC_TTL_SECONDS = 6 * 3600
_UPLOAD_ASYNC_MAX_JOBS = 300
_OCR_UPLOAD_TIMEOUT_SECONDS = int(getattr(settings, "upload_ocr_timeout_seconds", 120))


def _max_upload_bytes() -> int:
    mb = max(1, int(getattr(settings, "upload_max_mb", 20)))
    return mb * 1024 * 1024


def _is_pdf_signature(content: bytes) -> bool:
    # Semnătura standard PDF; ignorăm whitespace de la început.
    sample = (content or b"")[:16].lstrip()
    return sample.startswith(b"%PDF-")


def _pdf_signature_detail(content: bytes) -> str:
    sample = (content or b"")[:32].lstrip()
    upper = sample.upper()
    if upper.startswith(b"HTTP/"):
        return (
            "Fisierul nu este PDF real (pare raspuns web/redirect salvat ca .pdf). "
            "Deschide fisierul in browser si salveaza/exporta din nou PDF-ul original."
        )
    if upper.startswith(b"<!DOCTYPE") or upper.startswith(b"<HTML"):
        return (
            "Fisierul incarcat este pagina HTML, nu PDF. "
            "Re-descarca documentul folosind butonul de export PDF."
        )
    return "Fisierul incarcat nu are semnatura PDF valida."


def _ocr_timeout_seconds_for_upload(content_len: int, debug_mode: bool = False) -> int:
    # Timeout dinamic: scanuri mari + eventual retry DPI pe acelasi request pot depasi 5–8 min.
    base = max(60, int(_OCR_UPLOAD_TIMEOUT_SECONDS))
    mb = max(1.0, float(content_len or 0) / (1024.0 * 1024.0))
    extra = int(min(420, mb * 35))
    if debug_mode:
        extra += 120
    return base + extra


def _now_iso_utc() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _prune_upload_async_jobs() -> None:
    if upload_async_jobs_use_database():
        upload_async_jobs_prune_db(_UPLOAD_ASYNC_TTL_SECONDS, _UPLOAD_ASYNC_MAX_JOBS)
        return
    now_ts = datetime.utcnow().timestamp()
    with _UPLOAD_ASYNC_LOCK:
        to_delete: list[str] = []
        for jid, job in _UPLOAD_ASYNC_JOBS.items():
            finished_ts = float(job.get("finished_ts") or 0.0)
            if finished_ts and (now_ts - finished_ts) > _UPLOAD_ASYNC_TTL_SECONDS:
                to_delete.append(jid)
        for jid in to_delete:
            _UPLOAD_ASYNC_JOBS.pop(jid, None)

        if len(_UPLOAD_ASYNC_JOBS) <= _UPLOAD_ASYNC_MAX_JOBS:
            return
        ordered = sorted(
            _UPLOAD_ASYNC_JOBS.items(),
            key=lambda item: float(item[1].get("created_ts") or 0.0),
        )
        extra = len(_UPLOAD_ASYNC_JOBS) - _UPLOAD_ASYNC_MAX_JOBS
        for jid, _ in ordered[:extra]:
            _UPLOAD_ASYNC_JOBS.pop(jid, None)


def _set_upload_async_job(job_id: str, **fields) -> dict:
    if upload_async_jobs_use_database():
        return upload_async_job_merge_db(job_id, **fields)
    with _UPLOAD_ASYNC_LOCK:
        current = _UPLOAD_ASYNC_JOBS.get(job_id, {})
        current.update(fields)
        _UPLOAD_ASYNC_JOBS[job_id] = current
        return dict(current)


def _get_upload_async_job(job_id: str) -> Optional[dict]:
    if upload_async_jobs_use_database():
        return upload_async_job_get_db(job_id)
    with _UPLOAD_ASYNC_LOCK:
        job = _UPLOAD_ASYNC_JOBS.get(job_id)
        return dict(job) if job else None


def _rezultat_pare_gunoi(denumire: Optional[str], unitate: Optional[str]) -> bool:
    d = (denumire or "").strip()
    if not d:
        return True
    if len(d) <= 2:
        return True
    letters = sum(1 for ch in d if ch.isalpha())
    digits = sum(1 for ch in d if ch.isdigit())
    punct = sum(1 for ch in d if not ch.isalnum() and not ch.isspace())
    total = max(len(d), 1)
    if letters / total < 0.25 and digits / total < 0.20:
        return True
    if punct / total > 0.35:
        return True
    # Exemple de artefacte OCR: "ies", "a pea", "SN SAS..."
    if re.match(r"^[a-z]{1,4}$", d):
        return True
    u = (unitate or "").strip()
    if u and len(u) <= 2 and letters <= 3:
        return True
    return False


def _calc_upload_quality(parsed: Optional[PatientParsed]) -> dict:
    rezultate = list(getattr(parsed, "rezultate", []) or [])
    total_rez = len(rezultate)
    nec = sum(1 for r in rezultate if getattr(r, "analiza_standard_id", None) is None)
    zg = sum(
        1
        for r in rezultate
        if _rezultat_pare_gunoi(getattr(r, "denumire_raw", ""), getattr(r, "unitate", ""))
    )
    unknown_ratio = (nec / total_rez) if total_rez else 1.0
    noise_ratio = (zg / total_rez) if total_rez else 1.0
    unknown_name = (not parsed) or ((getattr(parsed, "nume", "") or "").strip().lower() == "necunoscut")
    return {
        "total_rez": total_rez,
        "nec": nec,
        "zg": zg,
        "unknown_ratio": float(unknown_ratio),
        "noise_ratio": float(noise_ratio),
        "unknown_name": bool(unknown_name),
    }


def _calc_triage_ai(parsed: Optional[PatientParsed], tip: str, ocr_metrics: Optional[dict]) -> dict:
    q = _calc_upload_quality(parsed)
    score = 100
    reasons: list[str] = []

    if q["unknown_name"]:
        score -= 25
        reasons.append("nume_necunoscut")
    # Penalizare numar analize: doar daca sub 3 (aproape gol)
    if q["total_rez"] < 3:
        score -= 20
        reasons.append("prea_putine_analize")
    # Prag ~20% „bun”: penalizare doar dacă necunoscute/zgomot depășesc 80%.
    if q["unknown_ratio"] > 0.80:
        score -= 20
        reasons.append("procent_necunoscute_mare")
    if q["noise_ratio"] > 0.80:
        score -= 20
        reasons.append("procent_zgomot_mare")

    ocr_summary = (ocr_metrics or {}).get("summary", {}) if isinstance(ocr_metrics, dict) else {}
    avg_conf = float(ocr_summary.get("avg_mean_conf", 0.0) or 0.0)
    avg_weak = float(ocr_summary.get("avg_weak_ratio", 1.0) or 1.0)
    # Nu penalizam OCR metrics in triage - un scan slab se salveaza oricum

    score = max(0, min(100, int(round(score))))
    decision = "auto"
    if score < 20:
        decision = "review"

    return {
        "score": score,
        "decision": decision,
        "reasons": reasons,
        "stats": {
            "total_analize": q["total_rez"],
            "unknown_ratio": round(q["unknown_ratio"], 3),
            "noise_ratio": round(q["noise_ratio"], 3),
            "avg_mean_conf": round(avg_conf, 2),
            "avg_weak_ratio": round(avg_weak, 3),
        },
    }


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


def _startup_blocking_work() -> None:
    """Migrari DB, admin implicit, curatare nume - sincron, ruleaza intr-un thread (nu blocheaza /health)."""
    print("[STARTUP][worker] start migratii si admin", flush=True)
    try:
        from backend.config import settings
        url = (settings.database_url or "").strip()
        if url and url.lower().startswith("postgresql"):
            import time
            from pathlib import Path
            sql_dir = Path(__file__).resolve().parent.parent / "sql"
            conn = None
            for attempt in range(3):
                try:
                    conn = _postgresql_connect(url)
                    break
                except Exception as e:
                    print(f"[STARTUP] DB connect attempt {attempt+1}/3: {e}")
                    time.sleep(1)
            if conn:
                conn.autocommit = False
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'pacienti'")
                    if cur.fetchone() is None:
                        for fname in ["001_schema.sql", "003_users_auth_postgres.sql", "004_pg_analize_extinse.sql", "005_pg_alias_fix.sql", "006_pg_alias_ocr.sql"]:
                            path = sql_dir / fname
                            if path.exists():
                                try:
                                    sql = path.read_text(encoding="utf-8")
                                    cur.execute(sql)
                                    conn.commit()
                                    print(f"[STARTUP] OK Schema PG: {fname}")
                                except Exception as ex:
                                    conn.rollback()
                                    print(f"[STARTUP] Schema PG {fname}: {ex}")
                    cur.close()
                except Exception as ex:
                    if conn:
                        conn.rollback()
                    print(f"[STARTUP] Schema PG init: {ex}")
                finally:
                    conn.close()
            sql_path = Path(__file__).resolve().parent.parent / "sql" / "007_ordine_categorie.sql"
            if sql_path.exists():
                conn = _postgresql_connect(url)
                conn.autocommit = False
                try:
                    cur = conn.cursor()
                    cur.execute(sql_path.read_text(encoding="utf-8"))
                    conn.commit()
                    print("[STARTUP] OK Migrare 007 (ordine, categorie)")
                except Exception as e:
                    conn.rollback()
                    if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                        print(f"[STARTUP] Migrare 007: {e}")
                finally:
                    conn.close()
            sql_008 = Path(__file__).resolve().parent.parent / "sql" / "008_pg_alias_bioclinica.sql"
            if url and sql_008.exists():
                try:
                    conn = _postgresql_connect(url)
                    conn.autocommit = False
                    try:
                        cur = conn.cursor()
                        cur.execute(sql_008.read_text(encoding="utf-8"))
                        conn.commit()
                        print("[STARTUP] OK Migrare 008 (alias Bioclinica)")
                    except Exception as ex:
                        conn.rollback()
                        if "already exists" not in str(ex).lower() and "duplicate" not in str(ex).lower():
                            print(f"[STARTUP] Migrare 008: {ex}")
                    finally:
                        conn.close()
                except Exception as ex:
                    print(f"[STARTUP] Migrare 008 (ignorat): {ex}")
            sql_009 = Path(__file__).resolve().parent.parent / "sql" / "009_pg_laboratoare_catalog.sql"
            if url and sql_009.exists():
                try:
                    conn = _postgresql_connect(url)
                    conn.autocommit = False
                    try:
                        cur = conn.cursor()
                        cur.execute(sql_009.read_text(encoding="utf-8"))
                        conn.commit()
                        print("[STARTUP] OK Migrare 009 (laboratoare, catalog)")
                    except Exception as ex:
                        conn.rollback()
                        if "already exists" not in str(ex).lower() and "duplicate" not in str(ex).lower():
                            print(f"[STARTUP] Migrare 009: {ex}")
                    finally:
                        conn.close()
                except Exception as ex:
                    print(f"[STARTUP] Migrare 009 (ignorat): {ex}")
            sql_010_pg = Path(__file__).resolve().parent.parent / "sql" / "010_pg_alias_laboratoare.sql"
            if url and sql_010_pg.exists():
                try:
                    conn = _postgresql_connect(url)
                    conn.autocommit = False
                    try:
                        cur = conn.cursor()
                        cur.execute(sql_010_pg.read_text(encoding="utf-8"))
                        conn.commit()
                        print("[STARTUP] OK Migrare 010 (alias laboratoare)")
                    except Exception as ex:
                        conn.rollback()
                        if "duplicate" not in str(ex).lower():
                            print(f"[STARTUP] Migrare 010: {ex}")
                    finally:
                        conn.close()
                except Exception as ex:
                    print(f"[STARTUP] Migrare 010 (ignorat): {ex}")
            sql_011 = Path(__file__).resolve().parent.parent / "sql" / "011_pg_valoare_text.sql"
            if url and sql_011.exists():
                try:
                    conn = _postgresql_connect(url)
                    conn.autocommit = False
                    try:
                        cur = conn.cursor()
                        cur.execute(sql_011.read_text(encoding="utf-8"))
                        conn.commit()
                        print("[STARTUP] OK Migrare 011 (valoare_text TEXT)")
                    except Exception as ex:
                        conn.rollback()
                        em = str(ex).lower()
                        if "already" not in em and "duplicate" not in em:
                            print(f"[STARTUP] Migrare 011: {ex}")
                    finally:
                        conn.close()
                except Exception as ex:
                    print(f"[STARTUP] Migrare 011 (ignorat): {ex}")
            sql_012 = Path(__file__).resolve().parent.parent / "sql" / "012_pg_necunoscuta_categorie.sql"
            if url and sql_012.exists():
                try:
                    conn = _postgresql_connect(url)
                    conn.autocommit = False
                    try:
                        cur = conn.cursor()
                        cur.execute(sql_012.read_text(encoding="utf-8"))
                        conn.commit()
                        print("[STARTUP] OK Migrare 012 (categorie necunoscute)")
                    except Exception as ex:
                        conn.rollback()
                        em = str(ex).lower()
                        if "already" not in em and "duplicate" not in em and "exists" not in em:
                            print(f"[STARTUP] Migrare 012: {ex}")
                    finally:
                        conn.close()
                except Exception as ex:
                    print(f"[STARTUP] Migrare 012 (ignorat): {ex}")
            for sql_name, sql_label in [
                ("018_pg_indexes.sql", "indexuri performanta"),
                ("019_pg_medlife_pdr_aliases.sql", "aliasuri MedLife PDR"),
            ]:
                sql_file = Path(__file__).resolve().parent.parent / "sql" / sql_name
                if url and sql_file.exists():
                    try:
                        conn = _postgresql_connect(url)
                        conn.autocommit = False
                        try:
                            cur = conn.cursor()
                            cur.execute(sql_file.read_text(encoding="utf-8"))
                            conn.commit()
                            print(f"[STARTUP] OK Migrare {sql_name} ({sql_label})")
                        except Exception as ex:
                            conn.rollback()
                            em = str(ex).lower()
                            if "already" not in em and "duplicate" not in em and "exists" not in em:
                                print(f"[STARTUP] Migrare {sql_name}: {ex}")
                        finally:
                            conn.close()
                    except Exception as ex:
                        print(f"[STARTUP] Migrare {sql_name} (ignorat): {ex}")
    except Exception as e:
        print(f"[STARTUP] Migrare 007 (ignorat): {e}")
    try:
        from backend.database import get_connection, _use_sqlite
        if _use_sqlite():
            sql_009_sqlite = Path(__file__).resolve().parent.parent / "sql" / "009_laboratoare_catalog.sql"
            if sql_009_sqlite.exists():
                conn = get_connection()
                try:
                    conn.executescript(sql_009_sqlite.read_text(encoding="utf-8"))
                    conn.commit()
                    print("[STARTUP] OK Migrare 009 SQLite (laboratoare)")
                except Exception as ex:
                    if "already exists" not in str(ex).lower():
                        print(f"[STARTUP] Migrare 009 SQLite: {ex}")
                finally:
                    conn.close()
            sql_010 = Path(__file__).resolve().parent.parent / "sql" / "010_alias_laboratoare.sql"
            if sql_010.exists():
                try:
                    conn = get_connection()
                    conn.executescript(sql_010.read_text(encoding="utf-8"))
                    conn.commit()
                    print("[STARTUP] OK Migrare 010 SQLite (alias laboratoare)")
                except Exception as ex:
                    if "UNIQUE constraint" not in str(ex):
                        print(f"[STARTUP] Migrare 010 SQLite: {ex}")
                finally:
                    conn.close()
            conn_cat = None
            try:
                conn_cat = get_connection()
                cur = conn_cat.execute("PRAGMA table_info(analiza_necunoscuta)")
                col_names = [row[1] for row in cur.fetchall()]
                if "categorie" not in col_names:
                    conn_cat.execute("ALTER TABLE analiza_necunoscuta ADD COLUMN categorie TEXT")
                    conn_cat.commit()
                    print("[STARTUP] OK SQLite: coloana categorie pe analiza_necunoscuta")
            except Exception as ex:
                if "duplicate" not in str(ex).lower():
                    print(f"[STARTUP] SQLite categorie necunoscute: {ex}")
            finally:
                if conn_cat:
                    try:
                        conn_cat.close()
                    except Exception:
                        pass
            conn_rm = None
            try:
                conn_rm = get_connection()
                cur_rm = conn_rm.execute("PRAGMA table_info(rezultate_analize)")
                col_rm = [row[1] for row in cur_rm.fetchall()]
                if "rezultat_meta" not in col_rm:
                    conn_rm.execute("ALTER TABLE rezultate_analize ADD COLUMN rezultat_meta TEXT")
                    conn_rm.commit()
                    print("[STARTUP] OK SQLite: coloana rezultat_meta pe rezultate_analize")
            except Exception as ex:
                if "duplicate" not in str(ex).lower():
                    print(f"[STARTUP] SQLite rezultat_meta: {ex}")
            finally:
                if conn_rm:
                    try:
                        conn_rm.close()
                    except Exception:
                        pass
            sql_015 = Path(__file__).resolve().parent.parent / "sql" / "015_alias_clinice_necunoscute.sql"
            if sql_015.exists():
                conn015 = None
                try:
                    conn015 = get_connection()
                    conn015.executescript(sql_015.read_text(encoding="utf-8"))
                    conn015.commit()
                    print("[STARTUP] OK Migrare 015 SQLite (alias clinice / microbiologie)")
                except Exception as ex:
                    if "UNIQUE constraint" not in str(ex) and "already exists" not in str(ex).lower():
                        print(f"[STARTUP] Migrare 015 SQLite: {ex}")
                finally:
                    if conn015:
                        try:
                            conn015.close()
                        except Exception:
                            pass
    except Exception as ex:
        print(f"[STARTUP] Migrare 009 SQLite (ignorat): {ex}")
    try:
        print("[STARTUP] Verificare/Creare utilizator admin...")
        result = ensure_default_admin()
        if result:
            print("[STARTUP] OK Utilizator admin creat (username: admin, password: admin123)")
        else:
            print("[STARTUP] OK Utilizator admin exista deja")
    except Exception as e:
        print(f"[STARTUP] Eroare la creare admin: {e}")
        import traceback
        traceback.print_exc()

    try:
        from backend.database import fix_pacienti_nume_cunoscuti, fix_pacienti_nume_gunoi, fix_pacienti_nume_curatare_completa
        corectati = fix_pacienti_nume_cunoscuti()
        n_gunoi = fix_pacienti_nume_gunoi()
        n_curatare = fix_pacienti_nume_curatare_completa()
        if corectati:
            print(f"[STARTUP] OK Nume corectate: {len(corectati)} pacienti cunoscuti")
        if n_gunoi:
            print(f"[STARTUP] OK Nume gunoi -> Necunoscut: {n_gunoi} pacienti")
        if n_curatare:
            print(f"[STARTUP] OK Curatare nume: {n_curatare} pacienti")
    except Exception as e:
        print(f"[STARTUP] Eroare la corectare nume (ignorat): {e}")


@app.on_event("startup")
async def startup_event():
    """Migrarile DB ruleaza intr-un thread daemon - /health disponibil imediat."""
    threading.Thread(
        target=_startup_blocking_work, daemon=True, name="db-migrations"
    ).start()
    print("[STARTUP] Thread migratii DB pornit; /health disponibil.", flush=True)


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

# Versiune parser (cresc la fiecare fix) - verifici pe /health ca deploy-ul e actual
_PARSER_VERSION = "medlife-tsv-bbox-20260331c-optimizat"

@app.get("/health")
async def health():
    """Returneaza 200 imediat - Railway healthcheck. Fara query DB."""
    from backend.config import settings
    url = (settings.database_url or "").strip()
    db_type = "postgresql" if url.lower().startswith("postgres") else "sqlite"
    # Afișează host-ul DB (fără parolă) pentru diagnostic
    db_host = ""
    try:
        import re
        m = re.search(r"@([^/]+)", url)
        if m:
            db_host = m.group(1)
    except Exception:
        pass
    return {"status": "ok", "database_type": db_type, "parser_version": _PARSER_VERSION, "db_host": db_host}


@app.get("/api/migrate")
@app.post("/api/migrate")
async def run_migrations():
    """Rulează migrările PostgreSQL dacă tabelele lipsesc. Accesează în browser pentru setup inițial."""
    from backend.config import settings
    url = (settings.database_url or "").strip()
    if not url or not url.lower().startswith("postgresql"):
        return {"ok": False, "detail": "Nu folosești PostgreSQL."}
    try:
        from pathlib import Path
        sql_dir = Path(__file__).resolve().parent.parent / "sql"
        conn = _postgresql_connect(url)
        conn.autocommit = False
        done = []
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'pacienti'")
            if cur.fetchone() is None:
                for fname in ["001_schema.sql", "003_users_auth_postgres.sql", "004_pg_analize_extinse.sql", "005_pg_alias_fix.sql", "006_pg_alias_ocr.sql", "007_ordine_categorie.sql", "008_pg_alias_bioclinica.sql", "009_pg_laboratoare_catalog.sql", "010_pg_alias_laboratoare.sql"]:
                    path = sql_dir / fname
                    if path.exists():
                        try:
                            sql_text = path.read_text(encoding="utf-8")
                            if "INSERT OR IGNORE" in sql_text.upper():
                                continue
                            cur.execute(sql_text)
                            conn.commit()
                            done.append(fname)
                        except Exception as ex:
                            conn.rollback()
                            return {"ok": False, "detail": f"Eroare {fname}: {str(ex)}", "done": done}
            else:
                for fname in ["007_ordine_categorie.sql", "008_pg_alias_bioclinica.sql", "009_pg_laboratoare_catalog.sql", "010_pg_alias_laboratoare.sql", "011_pg_valoare_text.sql", "012_pg_necunoscuta_categorie.sql", "014_pg_rezultat_meta.sql", "015_pg_alias_clinice_necunoscute.sql", "016_pg_pacienti_perf.sql", "017_pg_upload_async_jobs.sql", "018_pg_indexes.sql", "019_pg_medlife_pdr_aliases.sql"]:
                    path = sql_dir / fname
                    if path.exists():
                        try:
                            sql_text = path.read_text(encoding="utf-8")
                            if "INSERT OR IGNORE" in sql_text.upper():
                                continue
                            cur.execute(sql_text)
                            conn.commit()
                            done.append(fname)
                        except Exception as ex:
                            conn.rollback()
                            if "already exists" not in str(ex).lower() and "duplicate" not in str(ex).lower():
                                return {"ok": False, "detail": f"Eroare {fname}: {str(ex)}", "done": done}
            cur.close()
            return {"ok": True, "detail": "Migrări aplicate.", "done": done}
        finally:
            conn.close()
    except Exception as e:
        return {"ok": False, "detail": str(e)}


@app.get("/api/fix-schema")
@app.post("/api/fix-schema")
async def fix_schema():
    """Adaugă coloanele lipsă direct (ALTER TABLE IF NOT EXISTS). Fara fisiere SQL."""
    from backend.config import settings
    url = (settings.database_url or "").strip()
    if not url or not url.lower().startswith("postgresql"):
        return {"ok": False, "detail": "Nu folosești PostgreSQL."}
    fixes = [
        ("rezultat_meta", "ALTER TABLE rezultate_analize ADD COLUMN IF NOT EXISTS rezultat_meta TEXT"),
        ("necunoscuta_categorie", "ALTER TABLE analize_necunoscute ADD COLUMN IF NOT EXISTS categorie TEXT"),
    ]
    done, errors = [], []
    try:
        conn = _postgresql_connect(url)
        conn.autocommit = True
        cur = conn.cursor()
        for name, sql in fixes:
            try:
                cur.execute(sql)
                done.append(name)
            except Exception as ex:
                errors.append(f"{name}: {ex}")
        cur.close()
        conn.close()
        return {"ok": True, "done": done, "errors": errors}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


@app.get("/login")
async def login_redirect():
    """Redirect GET /login -> / (formularul de login e pe pagina principala)."""
    return RedirectResponse(url="/", status_code=302)


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


class BackfillNecunoscutaCategorieBody(BaseModel):
    """Backfill categorie (secțiune PDF) pentru analiza_necunoscuta din rezultate_analize."""

    dry_run: bool = True
    limit: Optional[int] = None


@app.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    """Schimba parola utilizatorului curent."""
    user = get_user_by_username(current_user["username"])
    if not user or not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Parola curenta incorecta.")
    if len(body.new_password.strip()) < 8:
        raise HTTPException(status_code=400, detail="Parola noua trebuie sa aiba minim 8 caractere.")
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
    if len((body.password or "").strip()) < 8:
        raise HTTPException(status_code=400, detail="Parola trebuie sa aiba minim 8 caractere.")
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


@app.post("/api/restore")
async def backup_restore(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Importa backup JSON. Doar admin. Adauga date peste existente."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Doar admin poate importa backup-ul.")
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Fișierul trebuie să fie JSON.")
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
        rez = restore_from_backup(data)
        return rez
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON invalid: {e}")
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Eroare la import: {str(e)}"},
        )


@app.post("/api/import-dictionar-excel")
async def import_dictionar_excel(
    file: UploadFile = File(None),
    current_user: dict = Depends(get_current_user),
):
    """Importă dictionar analize + aliasuri din Excel. Doar admin."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Doar admin.")
    try:
        from backend.import_dictionar import import_dictionar_excel as _do_import_dictionar
        root = Path(__file__).resolve().parent.parent
        xlsx_path = root / "dictionar_analize_300_1200_alias.xlsx"
        if file and file.filename and file.filename.lower().endswith(".xlsx"):
            source = await file.read()
        elif xlsx_path.exists():
            source = xlsx_path
        else:
            raise HTTPException(
                status_code=400,
                detail="Încarcă fișierul Excel (dictionar_analize_300_1200_alias.xlsx) sau pune-l în rădăcina proiectului.",
            )
        rez = _do_import_dictionar(source)
        if not rez.get("ok"):
            raise HTTPException(status_code=500, detail=rez.get("mesaj", "Eroare import"))
        return rez
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.post("/api/admin/backfill-necunoscuta-categorie")
async def admin_backfill_necunoscuta_categorie(
    body: BackfillNecunoscutaCategorieBody,
    current_user: dict = Depends(get_current_user),
):
    """
    Completează analiza_necunoscuta.categorie din rezultate (cel mai recent rând cu aceeași denumire_raw).
    Implicit dry_run=true (simulare). Doar utilizatorul admin.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Doar admin poate rula această operație.")
    try:
        return backfill_categorie_necunoscuta_din_rezultate(
            dry_run=body.dry_run,
            limit=body.limit,
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


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


import concurrent.futures as _cf

# Executor dedicat pentru joburi de upload (max 2 joburi OCR simultan).
# Rulam totul SINCRON in thread - evitam blocarea event loop-ului cu apeluri DB sincrone.
_UPLOAD_JOB_EXECUTOR = _cf.ThreadPoolExecutor(max_workers=2, thread_name_prefix="upload-job")


def _process_upload_sync_job(
    job_id: str,
    *,
    owner_username: str,
    filename: str,
    content: bytes,
    content_type: str,
) -> None:
    """Procesare completa PDF in thread sincron: OCR + parse + DB. Nu blocheaza event loop-ul."""
    _set_upload_async_job(
        job_id,
        status="processing",
        started_at=_now_iso_utc(),
        started_ts=datetime.utcnow().timestamp(),
    )
    tmp_path = None
    status_code = 500
    payload: dict = {"detail": "Eroare necunoscuta."}
    try:
        from backend.parser import parse_full_text
        from backend.pdf_processor import extract_text_with_metrics

        file_mb = float(len(content or b"")) / (1024.0 * 1024.0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        dpi_first: Optional[int] = None
        if file_mb >= 3.0:
            dpi_first = min(260, int(getattr(settings, "ocr_dpi_hint", 300)))

        # OCR complet sincron in thread
        text, tip, ocr_err, colored_tokens, extractor, ocr_metrics = extract_text_with_metrics(tmp_path, dpi_first)

        upload_warnings: list[str] = []
        if not (text or "").strip():
            w = "Nu s-a extras niciun text din PDF; buletinul se salvează oricum."
            if ocr_err:
                w += " " + str(ocr_err)
            upload_warnings.append(w)

        parsed = parse_full_text(text or "", cnp_optional=True)

        # Retry DPI daca numele e necunoscut
        if tip == "ocr" and (parsed.nume or "").strip().lower() == "necunoscut":
            dpi_retry = min(max(int(getattr(settings, "ocr_dpi_hint", 300)) + 80, 380), 400) if file_mb < 3.0 else min(max(int(getattr(settings, "ocr_dpi_hint", 300)) + 40, 320), 360)
            try:
                text2, tip2, ocr_err2, ct2, ext2, om2 = extract_text_with_metrics(tmp_path, dpi_retry)
                parsed2 = parse_full_text(text2 or "", cnp_optional=True)
                if parsed2 and ((parsed2.nume or "").strip().lower() != "necunoscut" or len(parsed2.rezultate) > len(parsed.rezultate)):
                    parsed, text, tip, colored_tokens, extractor, ocr_metrics = parsed2, text2, tip2, ct2 or colored_tokens, f"{ext2}+dpi{dpi_retry}", om2 or ocr_metrics
            except Exception:
                pass

        normalize_rezultate(parsed.rezultate)

        # Calitate OCR
        ocr_calitate_slaba_salvata = False
        if tip == "ocr":
            q = _calc_upload_quality(parsed)
            suspect_flags = sum([
                (parsed.nume or "").strip().lower() == "necunoscut",
                int(q["total_rez"]) < 3,
                float(q["unknown_ratio"]) > 0.80,
                float(q["noise_ratio"]) > 0.80,
            ])
            if suspect_flags >= 2:
                ocr_calitate_slaba_salvata = True
                upload_warnings.append("Calitate OCR slabă sau date incomplete: buletinul a fost salvat. Recomandăm verificarea cu AI sau corectarea manuală.")

        ocr_summary = (ocr_metrics or {}).get("summary", {}) if isinstance(ocr_metrics, dict) else {}
        if tip == "ocr" and ocr_summary:
            avg_conf = float(ocr_summary.get("avg_mean_conf", 0.0) or 0.0)
            avg_weak = float(ocr_summary.get("avg_weak_ratio", 1.0) or 1.0)
            if avg_conf < float(getattr(settings, "ocr_retry_min_mean_conf", 50.0)) or avg_weak > float(getattr(settings, "ocr_retry_max_weak_ratio", 0.40)):
                upload_warnings.append(f"OCR cu încredere scăzută (mean_conf={avg_conf:.1f}). Rezultatele au fost marcate pentru verificare.")
                for r in parsed.rezultate:
                    if "ocr_conf_scazut" not in r.review_reasons:
                        r.review_reasons.append("ocr_conf_scazut")
                    r.needs_review = True
            for r in parsed.rezultate:
                r.ocr_confidence = avg_conf
                if r.analiza_standard_id is None and "alias_necunoscut" not in r.review_reasons:
                    r.review_reasons.append("alias_necunoscut")
                    r.needs_review = True

        triage = _calc_triage_ai(parsed, tip, ocr_metrics)

        # Colored tokens
        if colored_tokens:
            for r in parsed.rezultate:
                if r.flag is None and r.valoare is not None:
                    val_str = str(r.valoare).rstrip("0").rstrip(".")
                    if val_str in colored_tokens or val_str.replace(".", ",") in colored_tokens:
                        r.flag = "L" if r.interval_min is not None and r.valoare < r.interval_min else "H"

        # DB sincron (in thread - OK)
        pacient = upsert_pacient(parsed.cnp, parsed.nume, parsed.prenume)
        if not pacient or pacient.get("id") is None:
            raise RuntimeError("Eroare la salvarea pacientului.")

        data_buletin = _extrage_data_buletin(text or "")
        buletin = insert_buletin(
            pacient_id=pacient["id"],
            data_buletin=data_buletin,
            laborator=None,
            fisier_original=filename,
        )
        if not buletin or buletin.get("id") is None:
            raise RuntimeError("Eroare la salvarea buletinului.")

        for idx, r in enumerate(parsed.rezultate):
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
                ordine=r.ordine,
                categorie=r.categorie,
                rezultat_meta=rezultat_meta_pentru_insert(
                    getattr(r, "organism_raw", None),
                    getattr(r, "rezultat_tip", None),
                    getattr(r, "needs_review", False),
                    getattr(r, "review_reasons", []),
                    getattr(r, "ocr_confidence", None),
                ),
            )

        status_code = 200
        payload = {
            "message": "PDF procesat cu succes.",
            "tip_extragere": tip,
            "extractor": extractor,
            "pacient": {"id": pacient["id"], "cnp": pacient["cnp"], "nume": pacient["nume"], "prenume": pacient.get("prenume")},
            "buletin_id": buletin["id"],
            "numar_analize": len(parsed.rezultate),
            "warnings": upload_warnings,
            "triere_ai": triage,
            "ocr_calitate_slaba_salvata": ocr_calitate_slaba_salvata,
        }
        print(f"[UPLOAD-ASYNC] OK job={job_id} file={filename!r} analize={len(parsed.rezultate)} tip={tip}")
    except Exception as ex:
        status_code = 500
        payload = {"detail": str(ex)[:800]}
        print(f"[UPLOAD-ASYNC] EROARE job={job_id} file={filename!r}: {ex}")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    done_state = "success" if status_code < 400 else "error"
    _set_upload_async_job(
        job_id,
        status=done_state,
        response_status=status_code,
        result=payload,
        finished_at=_now_iso_utc(),
        finished_ts=datetime.utcnow().timestamp(),
    )


@app.post("/upload-async")
async def upload_pdf_async(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if not file or not file.filename or not file.filename.lower().endswith(".pdf"):
        return JSONResponse(status_code=400, content={"detail": "Fisierul trebuie sa fie PDF."})
    if file.content_type and file.content_type.lower() not in _ALLOWED_PDF_MIME:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Tip fisier neacceptat ({file.content_type}). Sunt acceptate doar PDF-uri."},
        )
    content = await file.read()
    if len(content) > _max_upload_bytes():
        return JSONResponse(
            status_code=413,
            content={"detail": f"Fisierul depaseste limita de {settings.upload_max_mb} MB."},
        )
    if not _is_pdf_signature(content):
        return JSONResponse(
            status_code=400,
            content={"detail": _pdf_signature_detail(content)},
        )

    _prune_upload_async_jobs()
    created_ts = datetime.utcnow().timestamp()
    job_id = uuid4().hex
    _set_upload_async_job(
        job_id,
        owner=(current_user or {}).get("username", ""),
        file_name=file.filename,
        status="queued",
        created_at=_now_iso_utc(),
        created_ts=created_ts,
    )
    _UPLOAD_JOB_EXECUTOR.submit(
        _process_upload_sync_job,
        job_id,
        owner_username=(current_user or {}).get("username", ""),
        filename=file.filename,
        content=content,
        content_type=file.content_type or "application/pdf",
    )
    return {
        "job_id": job_id,
        "status": "queued",
        "file_name": file.filename,
    }


@app.get("/upload-async/{job_id}")
async def upload_pdf_async_status(job_id: str, current_user: dict = Depends(get_current_user)):
    job = _get_upload_async_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job inexistent sau expirat.")
    is_owner = (job.get("owner") or "") == (current_user or {}).get("username", "")
    if not is_owner and not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Nu ai acces la acest job.")

    status = job.get("status", "queued")
    # Stale job detector: daca procesarea dureaza >12 minute, workerul probabil a murit.
    # Marcam jobul ca "error" ca sa nu ramana blocat la infinit in polling.
    _STALE_MINUTES = 12
    if status in {"processing", "queued"}:
        ref_ts = job.get("started_ts") or job.get("created_ts") or 0
        if ref_ts and (datetime.utcnow().timestamp() - float(ref_ts)) > _STALE_MINUTES * 60:
            _set_upload_async_job(
                job_id,
                status="error",
                response_status=504,
                result={"detail": f"Procesarea a depasit {_STALE_MINUTES} minute. Workerul s-a oprit sau PDF-ul e prea complex. Incearca din nou."},
                finished_at=_now_iso_utc(),
                finished_ts=datetime.utcnow().timestamp(),
            )
            status = "error"
            job["result"] = {"detail": f"Procesarea a depasit {_STALE_MINUTES} minute. Workerul s-a oprit sau PDF-ul e prea complex. Incearca din nou."}
            job["response_status"] = 504
            print(f"[UPLOAD-ASYNC] STALE job={job_id} marcat error dupa {_STALE_MINUTES}min")

    result = {
        "job_id": job.get("job_id"),
        "status": status,
        "file_name": job.get("file_name"),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "response_status": job.get("response_status"),
    }
    if status in {"success", "error"}:
        result["result"] = job.get("result")
    return result


@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    debug: bool = Query(False, description="Returneaza info diagnostic (text extras, analize parse)"),
    traceback_debug: bool = Query(False, alias="traceback", description="Incluzand traceback complet in eroare"),
    current_user: dict = Depends(get_current_user),
):
    """Primeste PDF, extrage text (sau OCR), parseaza CNP + nume + analize, salveaza in DB."""
    tmp_path = None
    try:
        if not file or not file.filename or not file.filename.lower().endswith(".pdf"):
            return JSONResponse(status_code=400, content={"detail": "Fisierul trebuie sa fie PDF."})
        if file.content_type and file.content_type.lower() not in _ALLOWED_PDF_MIME:
            return JSONResponse(
                status_code=400,
                content={"detail": f"Tip fisier neacceptat ({file.content_type}). Sunt acceptate doar PDF-uri."},
            )
        content = await file.read()
        file_mb = float(len(content or b"")) / (1024.0 * 1024.0)
        if len(content) > _max_upload_bytes():
            return JSONResponse(
                status_code=413,
                content={"detail": f"Fisierul depaseste limita de {settings.upload_max_mb} MB."},
            )
        if not _is_pdf_signature(content):
            return JSONResponse(
                status_code=400,
                content={"detail": _pdf_signature_detail(content)},
            )
        debug = bool(debug and _is_admin(current_user))
        traceback_debug = bool(traceback_debug and _is_admin(current_user) and settings.upload_enable_detailed_errors)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        from backend.parser import parse_full_text
        from backend.pdf_processor import extract_text_with_metrics

        # OCR-ul pe PDF scanat poate dura mult; rulam in thread separat ca sa nu blocam serverul.
        # Timeout per-pass: previne blocare permanenta la Tesseract/PyMuPDF pe fisiere corupte.
        _ocr_pass_timeout = max(180, _ocr_timeout_seconds_for_upload(len(content or b"")))
        dpi_first: Optional[int] = None
        if file_mb >= 3.0:
            dpi_first = min(260, int(getattr(settings, "ocr_dpi_hint", 300)))
        text, tip, ocr_err, colored_tokens, extractor, ocr_metrics = await asyncio.wait_for(
            asyncio.to_thread(extract_text_with_metrics, tmp_path, dpi_first),
            timeout=float(_ocr_pass_timeout),
        )
        if debug:
            # Verificare fara salvare: CNP optional ca sa vezi analize chiar fara CNP in PDF
            from backend.parser import _linie_este_exclusa
            tdbg = text or ""
            parsed_dbg = parse_full_text(tdbg, cnp_optional=True)
            lines_raw = [l.strip() for l in tdbg.replace("\r", "\n").split("\n") if l.strip()]
            excluse = [(i, l) for i, l in enumerate(lines_raw) if _linie_este_exclusa(l)]
            normalize_rezultate(parsed_dbg.rezultate)
            triage_dbg = _calc_triage_ai(parsed_dbg, tip, ocr_metrics)
            analize_list = [
                {
                    "denumire": r.denumire_raw,
                    "valoare": r.valoare,
                    "unitate": r.unitate,
                    "needs_review": getattr(r, "needs_review", False),
                    "review_reasons": getattr(r, "review_reasons", []),
                }
                for r in parsed_dbg.rezultate
            ]
            return {
                "debug": True,
                "parser_version": _PARSER_VERSION,
                "tip_extragere": tip,
                "extractor": extractor,
                "ocr_metrics": ocr_metrics,
                "lungime_text": len(tdbg),
                "numar_linii": len(lines_raw),
                "text_primele_3000": tdbg[:6000] + ("..." if len(tdbg) > 6000 else ""),
                "linii_0_80": [f"{i}: {repr(l)}" for i, l in enumerate(lines_raw)],
                "linii_excluse": [f"{i}: {repr(l)}" for i, l in excluse[:100]],
                "cnp": parsed_dbg.cnp,
                "nume": parsed_dbg.nume,
                "prenume": parsed_dbg.prenume,
                "numar_analize": len(parsed_dbg.rezultate),
                "analize": analize_list,
                "triere_ai": triage_dbg,
            }
        text = text or ""
        upload_warnings: list[str] = []
        if not text.strip():
            w = "Nu s-a extras niciun text din PDF; buletinul se salvează oricum (fără linii de analize)."
            if ocr_err:
                w += " " + str(ocr_err)
            upload_warnings.append(w)
        parsed = parse_full_text(text, cnp_optional=True)
        if tip == "ocr":
            # Fallback DPI mai mare doar cand numele pacientului nu e detectat (nu impunem prag de analize).
            count_now = len(parsed.rezultate)
            unknown_name = (parsed.nume or "").strip().lower() == "necunoscut"
            if unknown_name:
                if file_mb >= 3.0:
                    dpi_retry = min(max(int(getattr(settings, "ocr_dpi_hint", 300)) + 40, 320), 360)
                else:
                    dpi_retry = max(int(getattr(settings, "ocr_dpi_hint", 300)) + 80, 380)
                try:
                    text2, tip2, ocr_err2, colored_tokens2, extractor2, ocr_metrics2 = await asyncio.wait_for(
                        asyncio.to_thread(extract_text_with_metrics, tmp_path, dpi_retry),
                        timeout=float(_ocr_pass_timeout),
                    )
                except Exception:
                    text2 = ""
                    tip2 = tip
                    ocr_err2 = "OCR retry eroare"
                    colored_tokens2 = []
                    extractor2 = extractor
                    ocr_metrics2 = ocr_metrics
                parsed2 = parse_full_text(text2, cnp_optional=True)
                if parsed2:
                    count2 = len(parsed2.rezultate)
                    name2 = (parsed2.nume or "").strip().lower()
                    is_better = (name2 != "necunoscut" and unknown_name) or (count2 > count_now)
                    if is_better:
                        parsed = parsed2
                        text = text2
                        tip = tip2
                        if ocr_err2:
                            ocr_err = ocr_err2
                        if colored_tokens2:
                            colored_tokens = colored_tokens2
                        if ocr_metrics2:
                            ocr_metrics = ocr_metrics2
                        extractor = f"{extractor2}+dpi{dpi_retry}"
        ocr_calitate_slaba_salvata = False
        if tip == "ocr":
            q = _calc_upload_quality(parsed)
            total_rez = int(q["total_rez"])
            unknown_ratio = float(q["unknown_ratio"])
            noise_ratio = float(q["noise_ratio"])
            suspect_flags = 0
            if (parsed.nume or "").strip().lower() == "necunoscut":
                suspect_flags += 1
            if total_rez < 3:
                suspect_flags += 1
            if unknown_ratio > 0.80:
                suspect_flags += 1
            if noise_ratio > 0.80:
                suspect_flags += 1
            # Doua+ semnale slabe: salvam oricum, dar UI afiseaza avertisment rosu + recomandare AI.
            if suspect_flags >= 2:
                ocr_calitate_slaba_salvata = True
        if not parsed.rezultate:
            upload_warnings.append(
                "Nu s-au extras analize din text; buletinul a fost salvat fără linii de rezultate. "
                "Poți folosi Verificare sau trimitere spre analiză (AI) când consideri."
            )
        normalize_rezultate(parsed.rezultate)
        if ocr_calitate_slaba_salvata:
            upload_warnings.append(
                "Calitate OCR slabă sau date incomplete: buletinul a fost salvat. "
                "Recomandăm verificarea cu AI sau corectarea manuală a analizelor."
            )
        ocr_summary = (ocr_metrics or {}).get("summary", {}) if isinstance(ocr_metrics, dict) else {}
        if tip == "ocr" and ocr_summary:
            avg_conf = float(ocr_summary.get("avg_mean_conf", 0.0) or 0.0)
            avg_weak = float(ocr_summary.get("avg_weak_ratio", 1.0) or 1.0)
            ocr_suspect = (
                avg_conf < float(getattr(settings, "ocr_retry_min_mean_conf", 50.0))
                or avg_weak > float(getattr(settings, "ocr_retry_max_weak_ratio", 0.40))
            )
            if ocr_suspect:
                upload_warnings.append(
                    f"OCR cu încredere scăzută (mean_conf={avg_conf:.1f}, weak_ratio={avg_weak:.2f}). "
                    "Rezultatele au fost marcate pentru verificare."
                )
                for r in parsed.rezultate:
                    if "ocr_conf_scazut" not in r.review_reasons:
                        r.review_reasons.append("ocr_conf_scazut")
                    r.needs_review = True
            for r in parsed.rezultate:
                r.ocr_confidence = avg_conf
                if r.analiza_standard_id is None and "alias_necunoscut" not in r.review_reasons:
                    r.review_reasons.append("alias_necunoscut")
                    r.needs_review = True
        triage = _calc_triage_ai(parsed, tip, ocr_metrics)
        if triage["decision"] in ("review", "ai"):
            upload_warnings.append(f"Triage document: {triage['decision'].upper()} (score={triage['score']}).")
            for r in parsed.rezultate:
                if triage["decision"] == "ai":
                    if "triere_ai" not in r.review_reasons:
                        r.review_reasons.append("triere_ai")
                else:
                    if "triere_review" not in r.review_reasons:
                        r.review_reasons.append("triere_review")
                r.needs_review = True
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
        try:
            pacient = upsert_pacient(parsed.cnp, parsed.nume, parsed.prenume)
        except Exception as ex:
            raise RuntimeError(f"Eroare la upsert_pacient: {ex}") from ex
        if not pacient or pacient.get("id") is None:
            raise RuntimeError("Eroare la salvarea pacientului. Verifica conexiunea la baza de date.")
        data_buletin = _extrage_data_buletin(text)
        try:
            buletin = insert_buletin(
            pacient_id=pacient["id"],
            data_buletin=data_buletin,
            laborator=None,
            fisier_original=file.filename,
        )
        except Exception as ex:
            raise RuntimeError(f"Eroare la insert_buletin: {ex}") from ex
        if not buletin or buletin.get("id") is None:
            raise RuntimeError("Eroare la salvarea buletinului. Verifica conexiunea la baza de date.")
        for idx, r in enumerate(parsed.rezultate):
            try:
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
                    ordine=r.ordine,
                    categorie=r.categorie,
                    rezultat_meta=rezultat_meta_pentru_insert(
                        getattr(r, "organism_raw", None),
                        getattr(r, "rezultat_tip", None),
                        getattr(r, "needs_review", False),
                        getattr(r, "review_reasons", []),
                        getattr(r, "ocr_confidence", None),
                    ),
                )
            except (IndexError, TypeError) as ex:
                raise RuntimeError(
                    f"Eroare la rezultatul {idx+1}/{len(parsed.rezultate)} "
                    f"(denumire: {getattr(r, 'denumire_raw', '?')[:50]}): {ex}"
                ) from ex
        return {
            "message": "PDF procesat cu succes.",
            "tip_extragere": tip,
            "extractor": extractor,
            "ocr_metrics": ocr_metrics,
            "pacient": {"id": pacient["id"], "cnp": pacient["cnp"], "nume": pacient["nume"], "prenume": pacient.get("prenume")},
            "buletin_id": buletin["id"],
            "data_buletin": buletin.get("data_buletin"),
            "numar_analize": len(parsed.rezultate),
            "numar_de_verificat": sum(1 for r in parsed.rezultate if getattr(r, "needs_review", False)),
            "warnings": upload_warnings,
            "triere_ai": triage,
            "ocr_calitate_slaba_salvata": ocr_calitate_slaba_salvata,
        }
    except Exception as e:
        tb = traceback.format_exc()
        try:
            _ERORI_LOG.write_text(tb, encoding="utf-8")
        except Exception:
            pass
        detail = str(e)
        status = 503 if ("connection" in detail.lower() or "role" in detail or "database" in detail.lower()) else 500
        include_tb = bool(traceback_debug)
        return JSONResponse(
            status_code=status,
            content={"detail": detail[:800], "traceback": tb if include_tb else None},
            media_type="application/json",
        )
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@app.get("/pacienti")
async def lista_pacienti(
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Lista pacienti paginata. ?q=text pentru cautare, ?limit=50&offset=0 pentru paginare."""
    items, total = get_pacienti_paginat(limit=limit, offset=offset, q=q)
    return {"items": items, "total": total}


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
    
    # 3. Grupeaza rezultatele în rânduri pentru matrice.
    # - Un singur buletin: câte înregistrări în DB, atâtea rânduri (cheie = id rezultat). Altfel
    #   denumire_raw goală sau identică pentru același cod standard colapsează totul (ex. 28 → 22).
    # - Mai multe buletine: cheie semantică (id standard, denumire raw, ordine) ca să alinieze coloanele
    #   în timp; ordine lipsește → folosim id rezultat doar ca fallback pentru cheie.
    n_buletine = len(buletine_sorted)
    analize_map = {}  # cheie -> {denumire, unitate, valori_dict: {buletin_id: (valoare, flag)}, categorie, ordine_min}
    
    for idx_buletin, b in enumerate(buletine_sorted):
        buletin_id = b.get("id")
        # Pentru aliniere intre buletine, folosim aparitia in ordinea PDF per analiza.
        # Astfel aceeasi analiza standard ramane pe acelasi rand chiar daca denumirea OCR variaza.
        aparitii_sid: dict[int, int] = {}
        aparitii_unknown: dict[str, int] = {}
        for rez in b.get("rezultate", []):
            raw = (rez.get("denumire_raw") or "").strip()
            sid = rez.get("analiza_standard_id")
            std = (rez.get("denumire_standard") or "").strip()
            rid = rez.get("id")
            if n_buletine == 1 and rid is not None:
                cheie = ("rez", int(rid))
            else:
                if sid is not None:
                    try:
                        sid_int = int(sid)
                    except (TypeError, ValueError):
                        sid_int = 0
                    aparitie = aparitii_sid.get(sid_int, 0)
                    aparitii_sid[sid_int] = aparitie + 1
                    cheie = ("m", sid_int, aparitie)
                else:
                    unk_label = re.sub(r"\s+", " ", (raw or std or "Necunoscuta").strip()).lower()
                    aparitie = aparitii_unknown.get(unk_label, 0)
                    aparitii_unknown[unk_label] = aparitie + 1
                    cheie = ("u", unk_label, aparitie)
            
            if cheie not in analize_map:
                # Etichetă rând: denumirea din PDF (raw) distinge liniile; fallback la standard din catalog
                label = (raw or std or "?").strip()
                analize_map[cheie] = {
                    "denumire_standard": label,
                    "unitate": rez.get("unitate") or "",
                    "valori_dict": {},
                    "categorie": rez.get("categorie") or "",
                    "ordine_min": rez.get("ordine") if rez.get("ordine") is not None else 99999,
                }
            else:
                # Actualizeaza ordinea minima (luam cea mai mica ordine din toate buletinele)
                ord_curent = rez.get("ordine")
                if ord_curent is not None and ord_curent < analize_map[cheie]["ordine_min"]:
                    analize_map[cheie]["ordine_min"] = ord_curent
                # Actualizeaza categoria daca lipseste
                if not analize_map[cheie]["categorie"] and rez.get("categorie"):
                    analize_map[cheie]["categorie"] = rez.get("categorie") or ""
            
            # Salveaza valoarea pentru acest buletin
            valoare = rez.get("valoare")
            if valoare is None and rez.get("valoare_text"):
                valoare = rez.get("valoare_text")
            
            analize_map[cheie]["valori_dict"][buletin_id] = (valoare, rez.get("flag") or "")
    
    # 4. Construieste lista finala de analize cu vectori de valori
    # Sortare: intai pe categorie (cu ordine_categorie), apoi pe ordine_min in PDF
    # Analizele fara categorie merg la sfarsit in ordine alfabetica
    _ORDINE_CATEGORIE = {
        "Hemoleucograma": 0,
        "Biochimie": 1,
        "Lipidograma": 2,
        "Coagulare": 3,
        "Examen urina": 4,
        "Electroforeza": 5,
        "Imunologie si Serologie": 6,
        "Hormoni tiroidieni": 7,
        "Hormoni": 8,
        "Markeri tumorali": 9,
        "Minerale si electroliti": 10,
        "Inflamatie": 11,
    }
    
    def _sort_key(cheie_info):
        cheie, info = cheie_info
        cat = info.get("categorie") or ""
        ord_cat = _ORDINE_CATEGORIE.get(cat, 999)
        ord_pdf = info.get("ordine_min", 99999)
        # Daca avem ordine din PDF, folosim ord_cat + ord_pdf
        # Altfel (date vechi fara ordine), sortam alfabetic in cadrul categoriei
        return (ord_cat, ord_pdf, info["denumire_standard"].lower())
    
    analize_result = []
    for cheie, info in sorted(analize_map.items(), key=_sort_key):
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
            "flags": flags,
            "categorie": info.get("categorie") or "",
        })

    # 5. Compactare rânduri complementare (aceeași analiză split-uită pe două rânduri).
    # Se unesc doar dacă nu există conflict de valoare/flag pe aceeași coloană.
    def _is_missing(v) -> bool:
        return v is None or (isinstance(v, str) and not v.strip())

    def _norm_cmp(v) -> str:
        if _is_missing(v):
            return ""
        return re.sub(r"\s+", " ", str(v).strip())

    merged_result = []
    for row in analize_result:
        den = (row.get("denumire_standard") or "").strip().lower()
        unt = (row.get("unitate") or "").strip().lower()
        cat = (row.get("categorie") or "").strip().lower()
        valori_row = list(row.get("valori") or [])
        flags_row = list(row.get("flags") or [])

        merged = False
        for target in merged_result:
            t_den = (target.get("denumire_standard") or "").strip().lower()
            t_unt = (target.get("unitate") or "").strip().lower()
            t_cat = (target.get("categorie") or "").strip().lower()
            if (den, unt, cat) != (t_den, t_unt, t_cat):
                continue

            compat = True
            t_valori = target.get("valori") or []
            t_flags = target.get("flags") or []
            for i in range(min(len(valori_row), len(t_valori))):
                v_new, v_old = valori_row[i], t_valori[i]
                if not _is_missing(v_new) and not _is_missing(v_old) and _norm_cmp(v_new) != _norm_cmp(v_old):
                    compat = False
                    break
                f_new, f_old = flags_row[i], t_flags[i]
                if not _is_missing(f_new) and not _is_missing(f_old) and _norm_cmp(f_new) != _norm_cmp(f_old):
                    compat = False
                    break
            if not compat:
                continue

            for i in range(min(len(valori_row), len(t_valori))):
                if _is_missing(t_valori[i]) and not _is_missing(valori_row[i]):
                    t_valori[i] = valori_row[i]
                if _is_missing(t_flags[i]) and not _is_missing(flags_row[i]):
                    t_flags[i] = flags_row[i]
            target["valori"] = t_valori
            target["flags"] = t_flags
            merged = True
            break

        if not merged:
            merged_result.append(row)
    analize_result = merged_result

    # 6. Collapse final: un singur rând per denumire analiză,
    # chiar dacă au rămas conflicte între upload-uri duplicate sau categorii.
    # Alegem cea mai "curată" valoare pentru fiecare coloană.
    def _pick_best_value(values: list):
        valid = [v for v in values if not _is_missing(v)]
        if not valid:
            return None
        numeric = []
        texty = []
        for v in valid:
            if isinstance(v, (int, float)):
                numeric.append(v)
                continue
            s = _norm_cmp(v)
            try:
                numeric.append(float(s.replace(",", ".")))
            except (TypeError, ValueError):
                texty.append(s)
        if numeric:
            return numeric[0]
        # Pentru text, preferăm varianta cea mai scurtă (evită șiruri OCR concatenate).
        texty = [t for t in texty if t]
        if not texty:
            return None
        return sorted(texty, key=lambda t: (len(t), t))[0]

    def _pick_best_flag(flags: list):
        valid = [_norm_cmp(f) for f in flags if not _is_missing(f)]
        return valid[0] if valid else ""

    collapsed = {}
    for row in analize_result:
        key = (row.get("denumire_standard") or "").strip().lower()
        if key not in collapsed:
            collapsed[key] = {
                "denumire_standard": row.get("denumire_standard"),
                "unitate": row.get("unitate"),
                "categorie": row.get("categorie"),
                "valori": list(row.get("valori") or []),
                "flags": list(row.get("flags") or []),
            }
            continue

        target = collapsed[key]
        t_vals = target.get("valori") or []
        t_flags = target.get("flags") or []
        s_vals = list(row.get("valori") or [])
        s_flags = list(row.get("flags") or [])
        n = min(len(t_vals), len(s_vals))
        for i in range(n):
            t_vals[i] = _pick_best_value([t_vals[i], s_vals[i]])
            t_flags[i] = _pick_best_flag([t_flags[i], s_flags[i]])
        target["valori"] = t_vals
        target["flags"] = t_flags

    analize_result = list(collapsed.values())
    
    rezultate_in_baza = sum(len(b.get("rezultate") or []) for b in buletine_sorted)
    return {
        "pacient": {
            "id": pacient_data.get("id"),
            "cnp": pacient_data.get("cnp"),
            "nume": pacient_data.get("nume"),
            "prenume": pacient_data.get("prenume")
        },
        "date_buletine": date_buletine,
        "buletine_ids": [b.get("id") for b in buletine_sorted],
        # Număr real de înregistrări în DB (poate coincide cu rândurile din tabel după fix grupare)
        "rezultate_in_baza": rezultate_in_baza,
        "analize": analize_result
    }


@app.get("/pacient/{cnp}")
async def get_pacient(cnp: str, current_user: dict = Depends(get_current_user)):
    """Pacientul cu CNP dat + toate buletinele + rezultatele."""
    result = get_pacient_cu_analize(cnp)
    if not result:
        raise HTTPException(status_code=404, detail="Pacient negasit.")
    return result


@app.patch("/pacient/{cnp}")
async def actualizeaza_pacient_nume(cnp: str, body: dict, current_user: dict = Depends(get_current_user)):
    """Actualizeaza numele si/sau prenumele unui pacient (corectie nume corupte ex: TGO ASAT)."""
    nume = (body.get("nume") or "").strip()
    prenume = (body.get("prenume"))
    if prenume is not None:
        prenume = str(prenume).strip() or None
    if not nume:
        raise HTTPException(status_code=400, detail="Numele nu poate fi gol.")
    ok = update_pacient_nume(cnp, nume, prenume)
    if not ok:
        raise HTTPException(status_code=404, detail="Pacient negasit.")
    return {"message": "Nume actualizat.", "pacient": get_pacient_cu_analize(cnp)}


@app.get("/laboratoare")
async def lista_laboratoare(current_user: dict = Depends(get_current_user)):
    """Lista laboratoare cu numar analize in catalog."""
    return get_laboratoare()


@app.get("/laboratoare/{laborator_id}/analize")
async def catalog_laborator(laborator_id: int, current_user: dict = Depends(get_current_user)):
    """Catalog analize pentru un laborator."""
    return get_laborator_analize(laborator_id)


@app.get("/analize-standard")
async def lista_analize_standard(current_user: dict = Depends(get_current_user)):
    """Lista tuturor tipurilor de analize din baza de date."""
    return get_all_analize_standard()


@app.post("/analize-standard")
async def adauga_analiza_std(body: AdaugaAnalizaStdBody, current_user: dict = Depends(get_current_user)):
    """Adauga o noua analiza standard (denumire + cod unic)."""
    denumire = body.denumire.strip()
    cod = body.cod.strip()
    if not denumire or not cod:
        raise HTTPException(status_code=400, detail="Denumirea si codul sunt obligatorii.")
    try:
        analiza = adauga_analiza_standard(denumire, cod)
        return analiza
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


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
                denumire = _row_get(row, 0 if _use_sqlite() else 'denumire_raw')
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
async def adauga_rezultat(buletin_id: int, body: AdaugaRezultatBody, current_user: dict = Depends(get_current_user)):
    """Adauga manual un rezultat intr-un buletin existent.
    Daca se specifica si analiza_standard_id, denumire_raw este salvata ca alias
    pentru a fi recunoscuta automat la upload-uri viitoare.
    """
    denumire = body.denumire_raw.strip()
    analiza_standard_id = body.analiza_standard_id
    row = add_rezultat_manual(
        buletin_id=buletin_id,
        analiza_standard_id=analiza_standard_id,
        denumire_raw=denumire,
        valoare=float(body.valoare),
        unitate=body.unitate,
        flag=body.flag,
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
async def aproba_alias(body: AprobaAliasBody, current_user: dict = Depends(get_current_user)):
    """
    Aprobare alias: asociaza o denumire_raw necunoscuta cu o analiza_standard.
    Body: { "denumire_raw": "...", "analiza_standard_id": 5 }
    sau { "necunoscuta_id": 12, "analiza_standard_id": 5 } (recomandat din UI – evită probleme cu ghilimele).
    """
    aid = body.analiza_standard_id
    raw = (body.denumire_raw or "").strip()
    nid = body.necunoscuta_id
    if nid is not None:
        nid_int = nid
        rows = get_necunoscute_by_ids([nid_int])
        if not rows:
            return JSONResponse(
                status_code=404,
                content={"detail": "Intrarea nu există sau este deja aprobată."},
            )
        raw = (rows[0].get("denumire_raw") or "").strip()
    if not raw or not aid:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Campuri obligatorii: analiza_standard_id și (denumire_raw sau necunoscuta_id)."
            },
        )
    from backend.normalizer import adauga_alias_nou

    ok = adauga_alias_nou(raw, int(aid))
    if ok:
        return {"ok": True, "mesaj": f"Alias '{raw}' asociat cu succes."}
    return JSONResponse(status_code=500, content={"detail": "Eroare la salvarea alias-ului."})


@app.post("/aproba-alias-bulk")
async def aproba_alias_bulk(body: AprobaAliasBulkBody, current_user: dict = Depends(get_current_user)):
    """
    Aprobare în masă: aceeași analiză standard pentru mai multe rânduri din analiza_necunoscuta.
    Body: { "necunoscuta_ids": [1, 2, 3], "analiza_standard_id": 5 }
    """
    ids = body.necunoscuta_ids or body.ids or []
    aid_int = body.analiza_standard_id
    if not isinstance(ids, list) or not ids:
        return JSONResponse(
            status_code=400,
            content={"detail": "Lista necunoscuta_ids este goală sau invalidă."},
        )

    rows = get_necunoscute_by_ids(ids)
    if not rows:
        return JSONResponse(
            status_code=404,
            content={"detail": "Nicio intrare neaprobată găsită pentru id-urile date."},
        )
    requested = set()
    for x in ids:
        try:
            requested.add(int(x))
        except (TypeError, ValueError):
            pass
    found_ids = {r.get("id") for r in rows}
    skipped_ids = sorted(requested - found_ids)

    denumiri = [(r.get("denumire_raw") or "").strip() for r in rows]
    denumiri = [d for d in denumiri if d]
    if not denumiri:
        return JSONResponse(status_code=400, content={"detail": "Denumiri goale."})

    from backend.normalizer import adauga_aliasuri_bulk

    result = adauga_aliasuri_bulk(denumiri, aid_int)
    if not result.get("ok"):
        return JSONResponse(
            status_code=500,
            content={"detail": result.get("error") or "Eroare la aprobare în masă."},
        )
    return {
        "ok": True,
        "mesaj": f"Asociate {result.get('processed', 0)} denumiri la analiza standard {aid_int}.",
        "processed": result.get("processed", 0),
        "rows_matched": len(rows),
        "skipped_ids": skipped_ids,
    }


@app.post("/invalideaza-cache-alias")
async def invalideaza_cache_alias(current_user: dict = Depends(get_current_user)):
    """Invalideaza cache-ul alias-urilor (dupa aprobari bulk) - asigura ca toate workerii invata."""
    from backend.normalizer import invalideaza_cache
    invalideaza_cache()
    return {"ok": True, "mesaj": "Cache alias invalidat."}


@app.post("/goleste-analize-asociate")
async def goleste_asociate(current_user: dict = Depends(get_current_user)):
    """Șterge toate intrările din analiza_necunoscuta și analiza_alias."""
    from backend.normalizer import invalideaza_cache
    result = goleste_analize_asociate()
    invalideaza_cache()
    return result


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
  .content { max-width: 1200px; margin: 0 auto; padding: 24px; }
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

  /* Lista simpla pacienti */
  .lista-pacienti-simpla {
    list-style: none; padding: 0; margin: 0;
  }
  .lista-pacienti-simpla li {
    border-bottom: 1px solid var(--border);
  }
  .lista-pacienti-simpla li:last-child {
    border-bottom: none;
  }
  .btn-pacient-link {
    display: block; width: 100%;
    background: none; border: none; cursor: pointer;
    text-align: left; padding: 10px 4px;
    font-size: 1rem; font-weight: 600;
    color: var(--text);
    transition: color 0.15s;
  }
  .btn-pacient-link:hover {
    color: var(--albastru);
  }
  .btn-sterge-pacient {
    background: none; border: none; cursor: pointer;
    color: var(--gri); font-size: 0.85rem; padding: 4px 8px;
    border-radius: 4px;
    transition: color 0.15s, background 0.15s;
  }
  .lista-pacienti-simpla li:hover .btn-sterge-pacient { display: inline-block; }
  .tabel-container .btn-sterge-pacient { display: inline-block; opacity: 0.6; }
  .tabel-container table tr:hover .btn-sterge-pacient { opacity: 1; }
  .btn-sterge-pacient:hover {
    color: var(--rosu); background: #fff0f0;
  }

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

  /* Separatoare categorii in tabelul de evolutie */
  .tabel-evolutie tr.sectiune-separator {
    background: var(--albastru-deschis) !important;
    pointer-events: none;
  }

  .tabel-evolutie tr.sectiune-separator td.sectiune-header {
    padding: 6px 12px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--albastru);
    border-top: 2px solid var(--albastru);
    border-bottom: 1px solid var(--border);
    background: var(--albastru-deschis) !important;
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
    padding: 10px 24px;
    background: linear-gradient(180deg, #e8eef2 0%, #f5f7f9 100%);
    border-bottom: 2px solid var(--albastru);
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    position: sticky;
    top: 0;
    z-index: 10;
    min-height: 44px;
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
  .tab-pacient-btn .tab-nume { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 140px; }
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

  /* Variantă 2: Tab-uri ca browser – interfață principală */
  .pacient-list-card { margin-bottom: 16px; }
  .pacient-list-card.collapsat .lista-pacienti-body { display: none; }
  .pacient-list-card .toggle-lista {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: #f0f4f8;
    border: 1px solid var(--border);
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.88rem;
    color: var(--albastru);
    margin-bottom: 8px;
  }
  .pacient-list-card .toggle-lista:hover { background: #e4eaf0; }
  .pacient-list-card.collapsat .toggle-lista .icon { transform: rotate(-90deg); }
  #continut-pacienti-dinamici { margin-top: 12px; }

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
    <div class="sub">Panou medic – v26.03.2026 | <span id="user-display"></span></div>
  </div>
  <div style="display:flex;gap:8px;align-items:center">
    <button class="btn-logout" id="btn-header-backup" onclick="exportBackup(this)" style="display:none" title="Exportă backup înainte de redeploy (Railway)">📥 Export backup</button>
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
      <div style="margin-top:16px;">
        <div style="display:flex; flex-direction:column; gap:10px;">
          <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
            <button class="btn btn-primary" id="btn-upload" onclick="trimite(false)" disabled>
              <span id="btn-text">Procesează PDF</span>
            </button>
            <button class="btn btn-secondary" id="btn-verificare" onclick="trimite(true)" disabled title="Previzualizare fără salvare în DB"
              style="border:2px solid #0a7ea4;color:#0a7ea4;background:#e8f4f8;font-weight:600;padding:10px 16px">
              🔍 Verificare (fără salvare)
            </button>
            <span id="prog" style="font-size:0.85rem;color:var(--gri)"></span>
          </div>
          <p style="font-size:0.8rem;color:#0a7ea4;margin:0">« Verificare: vezi ce analize s-ar extrage, fără să salvezi în baza de date.</p>
        </div>
      </div>
      <div id="upload-out"></div>
    </div>
    <div class="card" id="card-pacienti-recenti" style="display:none">
      <h2>Pacienți încărcați</h2>
      <div id="lista-recenti" style="max-height:400px;overflow-y:auto"></div>
    </div>
  </div>

  <!-- TAB 2: Pacient (variantă 2 – tab-uri ca browser, analize vizibile sus) -->
  <div id="tab-pacient" class="sectiune">
    <div class="card pacient-list-card" id="card-lista-pacienti">
      <div class="toggle-lista" id="toggle-lista-pacienti" onclick="toggleListaPacienti()" style="display:none" title="Arată/ascunde lista">
        <span class="icon">▼</span> <span>Caută / Arată lista pacienți</span>
      </div>
      <div class="lista-pacienti-body">
        <h2>Caută pacient după CNP sau Nume</h2>
        <div class="search-row">
          <input class="input-search" id="q-pacient" placeholder="Introduceți CNP sau Nume…" oninput="cautaPacient(this.value)">
        </div>
        <div id="lista-pacienti"></div>
      </div>
    </div>
    <div id="continut-pacienti-placeholder" style="padding:40px 24px;color:var(--gri);text-align:center;font-size:0.95rem;border:2px dashed var(--border);border-radius:12px;background:#fafbfc">
      👤 Selectați un pacient din listă (buton Analize) – se deschide într-un tab pentru comutare rapidă
    </div>
    <div id="continut-pacienti-dinamici" style="display:none"></div>
  </div>

  <!-- TAB 3: Evolutie analiza pacient -->
  <div id="tab-analiza" class="sectiune">

    <!-- Card: Adauga analiza standard noua -->
    <div class="card" style="margin-bottom:20px">
      <h2>➕ Adaugă tip de analiză nouă</h2>
      <p style="font-size:0.85rem;color:var(--gri);margin-bottom:16px">
        Dacă o analiză nu apare în lista de tipuri, o poți adăuga aici.<br>
        <strong>Codul</strong> trebuie să fie unic (ex: CALCIU_IONIC, TSH, HGB).
      </p>
      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end">
        <div>
          <div style="font-size:0.78rem;color:var(--gri);margin-bottom:4px">Denumire analiză *</div>
          <input type="text" id="new-std-denumire" placeholder="ex: Calciu ionic (Ca2+)"
            style="padding:8px 10px;width:260px;font-size:0.9rem;border:1.5px solid #ccc;border-radius:6px" />
        </div>
        <div>
          <div style="font-size:0.78rem;color:var(--gri);margin-bottom:4px">Cod unic *</div>
          <input type="text" id="new-std-cod" placeholder="ex: CALCIU_IONIC"
            style="padding:8px 10px;width:160px;font-size:0.9rem;border:1.5px solid #ccc;border-radius:6px;text-transform:uppercase" />
        </div>
        <button class="btn btn-primary" onclick="adaugaAnalizaStandard()" style="padding:8px 18px">
          ➕ Adaugă
        </button>
      </div>
      <div id="msg-new-std" style="margin-top:10px;font-size:0.85rem"></div>

      <!-- Lista analize standard existente -->
      <div style="margin-top:20px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <strong style="font-size:0.9rem">Analize standard existente (<span id="cnt-std">0</span>)</strong>
          <input type="text" id="cauta-std" placeholder="🔍 caută..." oninput="filtreazaStd(this.value)"
            style="padding:5px 10px;font-size:0.82rem;border:1.5px solid #ccc;border-radius:6px;width:200px" />
        </div>
        <div id="lista-std" style="max-height:300px;overflow-y:auto;border:1px solid #e0e0e0;border-radius:6px">
          <p style="padding:12px;color:var(--gri)">Se încarcă…</p>
        </div>
      </div>
    </div>

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
      <div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap">
        <button class="btn btn-secondary" onclick="incarcaNecunoscute()">🔄 Reîncarcă lista</button>
        <button class="btn btn-secondary" onclick="golesteAnalizeAsociate()" style="color:var(--rosu)" title="Șterge toate analizele necunoscute și alias-urile (asocierile)">🗑️ Șterge toate asocierile</button>
      </div>
      <div id="nec-bulk-bar" style="display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:14px;padding:12px 14px;background:var(--albastru-deschis);border-radius:8px;border:1px solid var(--border)">
        <strong style="font-size:0.85rem">Aprobare în masă</strong>
        <span id="nec-bulk-count" style="font-size:0.82rem;color:var(--gri)">0 selectate</span>
        <select id="sel-std-bulk" style="padding:6px 10px;min-width:240px;max-width:100%;font-size:0.85rem;border:1px solid var(--border);border-radius:6px">
          <option value="">— Analiză standard (pentru rândurile bifate) —</option>
        </select>
        <button type="button" class="btn btn-primary" style="padding:6px 14px;font-size:0.82rem" onclick="aprobaAliasBulk()">✓ Asociază selectate</button>
      </div>
      <p style="font-size:0.78rem;color:var(--gri);margin:-6px 0 12px 0">
        Bifează mai multe rânduri dacă aceleași variante OCR trebuie mapate dintr-o dată la aceeași analiză standard (alias + actualizare retroactivă a rezultatelor, ca la un singur click).
      </p>
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
        <input type="password" class="input-search" id="setari-parola-noua" placeholder="Parola nouă (min. 8 caractere)">
        <input type="password" class="input-search" id="setari-parola-confirma" placeholder="Confirmă parola nouă">
        <button class="btn btn-primary" onclick="schimbaParola()">Salvează parola</button>
      </div>
      <p id="setari-msg-parola" style="margin-top:10px;font-size:0.88rem;display:none"></p>
    </div>
    <div class="card">
      <h2>Catalog laboratoare</h2>
      <p style="font-size:0.88rem;color:var(--gri);margin-bottom:12px">Laboratoare cu analize înregistrate în catalog.</p>
      <div id="lista-laboratoare"><p style="color:var(--gri)">Se încarcă…</p></div>
    </div>
    <div class="card" id="card-backup" style="display:none">
      <h2>Backup baza de date</h2>
      <p style="font-size:0.88rem;color:var(--gri);margin-bottom:12px">Exportă backup înainte de redeploy (Railway). Descarcă o copie de siguranță a pacienților, buletinelor și rezultatelor (fișier JSON).</p>
      <p id="setari-db-type" style="font-size:0.82rem;margin-bottom:12px;padding:6px 10px;background:#f0f7ff;border-radius:6px;display:none"></p>
      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin-bottom:16px">
        <button class="btn btn-primary" id="btn-export-backup" onclick="exportBackup(this)">Exportă backup</button>
        <div>
          <input type="file" id="input-restore" accept=".json" style="display:none" onchange="importBackup(this)">
          <button class="btn btn-secondary" id="btn-import-backup" onclick="document.getElementById('input-restore').click()">Importă backup</button>
        </div>
      </div>
      <p id="setari-msg-restore" style="font-size:0.88rem;display:none"></p>
      <hr style="margin:24px 0;border:none;border-top:1px solid #e0e0e0">
      <h3 style="font-size:1rem;margin-bottom:8px">Import dictionar analize (Excel)</h3>
      <p style="font-size:0.88rem;color:var(--gri);margin-bottom:12px">Importă ~300 analize standard și ~800 aliasuri. Înlocuiește alias-urile existente.<br><small>„Importă din proiect” necesită fișierul <code>dictionar_analize_300_1200_alias.xlsx</code> în rădăcina proiectului (și în git pentru Railway). Dacă importul eșuează prin timeout (Railway), rulați local: <code>railway run python import_dictionar_excel.py</code></small></p>
      <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin-bottom:16px">
        <div>
          <input type="file" id="input-dictionar-excel" accept=".xlsx" style="display:none" onchange="importDictionarExcel(this)">
          <button class="btn btn-primary" onclick="document.getElementById('input-dictionar-excel').click()">📂 Încarcă Excel și importă</button>
        </div>
        <button class="btn btn-secondary" onclick="importDictionarExcelAuto()">📥 Importă din proiect</button>
      </div>
      <p id="setari-msg-dictionar" style="font-size:0.88rem;display:none"></p>
      <hr style="margin:24px 0;border:none;border-top:1px solid #e0e0e0">
      <h3 style="font-size:1rem;margin-bottom:8px">Categorii – analize necunoscute</h3>
      <p style="font-size:0.88rem;color:var(--gri);margin-bottom:12px">
        Completează coloana „secțiune PDF” pentru rândurile din <strong>analize necunoscute</strong>, copiind-o din rezultatele deja salvate (același text din buletin).
        <strong>Simulare</strong> nu modifică baza de date.
      </p>
      <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:8px">
        <button type="button" class="btn btn-secondary" onclick="backfillNecunoscutaCategorie(true)">🔍 Simulare backfill</button>
        <button type="button" class="btn btn-primary" onclick="backfillNecunoscutaCategorie(false)">✓ Aplică în baza de date</button>
      </div>
      <p id="setari-msg-backfill-nec" style="font-size:0.88rem;display:none"></p>
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

<script>
// ─── Tab-uri dinamice pacienti ───────────────────────────────────────────────
const _tabPacienti = {};   // { cnp: { nume, html } }
let _tabPacientActiv = null;
let _veziPacientAbortController = null;

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
    _colapseazaListaPacienti();
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

function toggleListaPacienti() {
  const card = document.getElementById('card-lista-pacienti');
  if (card) card.classList.toggle('collapsat');
}

function _colapseazaListaPacienti() {
  const card = document.getElementById('card-lista-pacienti');
  const toggle = document.getElementById('toggle-lista-pacienti');
  if (card) card.classList.add('collapsat');
  if (toggle) toggle.style.display = 'inline-flex';
}

function _expandListaPacienti() {
  const card = document.getElementById('card-lista-pacienti');
  const toggle = document.getElementById('toggle-lista-pacienti');
  if (card) card.classList.remove('collapsat');
  if (toggle) toggle.style.display = 'none';
}

function activeazaTabPacient(cnp) {
  const continutDinamic = document.getElementById('continut-pacienti-dinamici');
  const placeholder = document.getElementById('continut-pacienti-placeholder');

  document.querySelectorAll('.tab-btn').forEach((b,i) => b.classList.toggle('activ', ['upload','pacient','analiza','alias','setari'][i] === 'pacient'));
  document.querySelectorAll('.sectiune').forEach(s => s.classList.remove('activa'));
  document.getElementById('tab-pacient').classList.add('activa');

  continutDinamic.style.display = '';
  if (placeholder) placeholder.style.display = 'none';
  document.querySelectorAll('.tab-pacient-btn').forEach(b => b.classList.remove('activ'));
  const btn = document.querySelector('.tab-pacient-btn[data-cnp="' + cnp + '"]');
  if (btn) btn.classList.add('activ');

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
    const placeholder = document.getElementById('continut-pacienti-placeholder');
    if (placeholder) placeholder.style.display = '';
    _expandListaPacienti();
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
function handle401(r) {
  if (r && r.status === 401) { clearToken(); location.reload(); return true; }
  return false;
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
      incarcaRecenti();
      (async () => {
        try {
          const r = await fetch('/analize-necunoscute', { headers: getAuthHeaders() });
          if (handle401(r)) return;
          const lista = r.ok ? await r.json() : [];
          const badge = document.getElementById('badge-nec');
          if (lista.length > 0 && badge) { badge.textContent = lista.length; badge.style.display = ''; }
        } catch {}
      })();
      return;
    }
    if (r.status === 401) clearToken();
  } catch {}
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
  const msgBf = document.getElementById('setari-msg-backfill-nec');
  if (msgBf) { msgBf.style.display = 'none'; msgBf.textContent = ''; }
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
      (async function() {
        try {
          const h = await fetch('/health');
          const d = await h.json();
          const el = document.getElementById('setari-db-type');
          if (el && d.database_type) {
            el.style.display = '';
            el.innerHTML = d.database_type === 'postgresql'
              ? '✅ <strong>PostgreSQL</strong> – datele persistă la redeploy'
              : '⚠️ <strong>SQLite</strong> – datele se pierd la redeploy. Adaugă PostgreSQL în Railway.';
          }
        } catch {}
      })();
    } else {
      card.style.display = 'none';
      if (cardBackup) cardBackup.style.display = 'none';
    }
  } catch {
    card.style.display = 'none';
    if (cardBackup) cardBackup.style.display = 'none';
  }
  incarcaLaboratoare();
}

async function incarcaLaboratoare() {
  const el = document.getElementById('lista-laboratoare');
  if (!el) return;
  try {
    const r = await fetch('/laboratoare', { headers: getAuthHeaders() });
    if (!r.ok) throw new Error('Eroare');
    const labs = await r.json();
    if (!labs || labs.length === 0) {
      el.innerHTML = '<p style="color:var(--gri);font-size:0.88rem">Niciun laborator în catalog. Rulează: <code>python scripts/import_lab_data.py</code></p>';
      return;
    }
    let html = '<div style="display:flex;flex-direction:column;gap:8px">';
    for (const lab of labs) {
      html += '<div style="border:1px solid #e0e0e0;border-radius:6px;padding:10px 14px">';
      html += '<strong>' + escHtml(lab.nume) + '</strong>';
      if (lab.website) html += ' <a href="' + escHtml(lab.website) + '" target="_blank" style="font-size:0.8rem;color:var(--albastru)">site</a>';
      html += ' <span style="font-size:0.8rem;color:var(--gri)">(' + (lab.nr_analize || 0) + ' analize)</span>';
      html += '<button type="button" class="btn btn-secondary" style="margin-left:10px;padding:4px 10px;font-size:0.8rem" onclick="veziCatalogLaborator(' + lab.id + ',\'' + escHtml(lab.nume).replace(/'/g,"\\'") + '\')">Vezi catalog</button>';
      html += '</div>';
    }
    html += '</div>';
    el.innerHTML = html;
  } catch (e) {
    el.innerHTML = '<p style="color:var(--rosu)">Eroare la încărcare.</p>';
  }
}

async function veziCatalogLaborator(id, nume) {
  try {
    const r = await fetch('/laboratoare/' + id + '/analize', { headers: getAuthHeaders() });
    if (!r.ok) throw new Error('Eroare');
    const analize = await r.json();
    const lines = analize.map(a => escHtml(a.denumire_standard) + (a.cod_standard ? ' <span style="color:#999">(' + escHtml(a.cod_standard) + ')</span>' : ''));
    alert('Catalog ' + nume + ':\\n\\n' + (lines.length ? lines.join('\\n') : '(gol)'));
  } catch (e) {
    alert('Eroare: ' + e.message);
  }
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

async function importBackup(inputEl) {
  const file = inputEl?.files?.[0];
  if (!file) return;
  const msgEl = document.getElementById('setari-msg-restore');
  const btnEl = document.getElementById('btn-import-backup');
  msgEl.style.display = '';
  msgEl.style.color = 'var(--gri)';
  msgEl.textContent = 'Se importă…';
  btnEl.disabled = true;
  try {
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch('/api/restore', {
      method: 'POST',
      body: fd,
      headers: getAuthHeaders()
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      msgEl.style.color = 'var(--rosu)';
      msgEl.textContent = j.detail || 'Eroare ' + r.status;
      return;
    }
    const parts = [];
    if (j.pacienti) parts.push(j.pacienti + ' pacienți');
    if (j.buletine) parts.push(j.buletine + ' buletine');
    if (j.rezultate) parts.push(j.rezultate + ' rezultate');
    msgEl.style.color = 'var(--verde)';
    msgEl.textContent = 'Import reușit: ' + (parts.length ? parts.join(', ') : 'date adăugate');
    if (j.erori && j.erori.length) {
      msgEl.textContent += '. Avertismente: ' + j.erori.slice(0, 3).join('; ');
    }
    inputEl.value = '';
    incarcaRecenti();
  } catch (e) {
    msgEl.style.color = 'var(--rosu)';
    msgEl.textContent = 'Eroare: ' + (e.message || '');
  } finally {
    btnEl.disabled = false;
  }
}

async function importDictionarExcel(inputEl) {
  const file = inputEl?.files?.[0];
  if (!file || !file.name.toLowerCase().endsWith('.xlsx')) return;
  const msgEl = document.getElementById('setari-msg-dictionar');
  msgEl.style.display = '';
  msgEl.style.color = 'var(--gri)';
  msgEl.textContent = 'Se importă… (poate dura 2-3 minute, nu închideți pagina)';
  try {
    const fd = new FormData();
    fd.append('file', file);
    const r = await fetch('/api/import-dictionar-excel', {
      method: 'POST',
      body: fd,
      headers: getAuthHeaders()
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      msgEl.style.color = 'var(--rosu)';
      msgEl.textContent = j.detail || 'Eroare ' + r.status;
      return;
    }
    msgEl.style.color = 'var(--verde)';
    msgEl.textContent = (j.mesaj || '') + ' Analize: ' + (j.analize_unic||0) + ', Aliasuri: ' + (j.aliasuri_procesate||0);
    if (j.erori) msgEl.textContent += '. Erori: ' + j.erori;
    inputEl.value = '';
  } catch (e) {
    msgEl.style.color = 'var(--rosu)';
    msgEl.textContent = 'Eroare: ' + (e.message || '');
  }
}

async function backfillNecunoscutaCategorie(dryRun) {
  const msg = document.getElementById('setari-msg-backfill-nec');
  if (!msg) return;
  if (!dryRun && !confirm('Aplicați actualizarea categoriilor în baza de date? (Doar pentru rândurile fără categorie)')) return;
  msg.style.display = 'block';
  msg.style.color = 'var(--gri)';
  msg.textContent = 'Se rulează…';
  try {
    const r = await fetch('/api/admin/backfill-necunoscuta-categorie', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ dry_run: dryRun })
    });
    const j = await r.json().catch(() => ({}));
    if (handle401(r)) return;
    if (!r.ok) {
      msg.style.color = 'var(--rosu)';
      msg.textContent = (typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail || j)) || ('Eroare ' + r.status);
      return;
    }
    msg.style.color = 'var(--verde)';
    msg.textContent =
      (j.dry_run ? '[Simulare] ' : '') +
      'Examinat: ' + j.examinat +
      ', cu categorie găsită: ' + j.cu_categorie_gasita +
      ', fără sursă în rezultate: ' + j.fara_categorie_in_rezultate +
      (j.dry_run ? ', ar fi actualizate: ' + j.actualizate : ', actualizate: ' + j.actualizate);
    if (j.dry_run && j.cu_categorie_gasita > 0) {
      msg.textContent += ' — folosiți „Aplică în baza de date” pentru a salva.';
    }
    if (!j.dry_run && j.actualizate > 0) {
      _analize_std_cache = null;
      try { incarcaNecunoscute(); } catch (e) {}
    }
  } catch (e) {
    msg.style.color = 'var(--rosu)';
    msg.textContent = 'Eroare: ' + (e.message || '');
  }
}

async function importDictionarExcelAuto() {
  const msgEl = document.getElementById('setari-msg-dictionar');
  msgEl.style.display = '';
  msgEl.style.color = 'var(--gri)';
  msgEl.textContent = 'Se importă din proiect… (poate dura 2-3 minute, nu închideți pagina)';
  try {
    const r = await fetch('/api/import-dictionar-excel', {
      method: 'POST',
      headers: getAuthHeaders()
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      msgEl.style.color = 'var(--rosu)';
      msgEl.textContent = j.detail || 'Eroare ' + r.status;
      return;
    }
    msgEl.style.color = 'var(--verde)';
    msgEl.textContent = (j.mesaj || '') + ' Analize: ' + (j.analize_unic||0) + ', Aliasuri: ' + (j.aliasuri_procesate||0);
    if (j.erori) msgEl.textContent += '. Erori: ' + j.erori;
  } catch (e) {
    msgEl.style.color = 'var(--rosu)';
    msgEl.textContent = 'Eroare: ' + (e.message || '');
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
    msg.textContent = 'Parola nouă trebuie să aibă minim 8 caractere.';
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
    msg.textContent = 'Parola trebuie să aibă minim 8 caractere.';
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
  if (id === 'pacient') {
    clearTimeout(_cautaPacientTimer);
    const inp = document.getElementById('q-pacient');
    if (inp) inp.value = '';
    incarcaListaPacienti('');
  }
  if (id === 'alias') incarcaNecunoscute();
  if (id === 'setari') incarcaSetari();
  if (id === 'analiza') incarcaAnalizeleStandard();
}

// ─── Upload ──────────────────────────────────────────────────────────────────
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
let fisierSelectat = [];

fileInput.onchange = e => { void selecteazaFisiere(Array.from(e.target.files)); };

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  void selecteazaFisiere(Array.from(e.dataTransfer.files));
});

/** Citește primii octeți și verifică semnătura reală %PDF- (nu doar extensia .pdf). */
async function _verificaContinutPdfReal(file) {
  const n = Math.min(file.size || 0, 2048);
  if (n < 5) return { ok: false, cod: 'gol', mesaj: 'Fișierul este gol sau prea mic.' };
  const ab = await file.slice(0, n).arrayBuffer();
  const b = new Uint8Array(ab);
  let i = 0;
  while (i < b.length && (b[i] === 9 || b[i] === 10 || b[i] === 13 || b[i] === 32)) i++;
  if (i + 5 > b.length) return { ok: false, cod: 'necunoscut', mesaj: 'Nu începe cu un PDF valid.' };
  const sig = String.fromCharCode(b[i], b[i+1], b[i+2], b[i+3], b[i+4]);
  if (sig === '%PDF-') return { ok: true };
  let head = '';
  for (let j = 0; j < Math.min(48, b.length - i); j++) head += String.fromCharCode(b[i + j]);
  const u = head.toUpperCase();
  if (u.startsWith('HTTP/')) {
    return {
      ok: false,
      cod: 'http',
      mesaj: 'Fișierul nu este PDF: conține un răspuns HTTP (redirect sau eroare de la site), salvat greșit cu extensia .pdf. '
        + 'Deschide rezultatul în browser, așteaptă să se încarce buletinul, apoi folosește „Print / Imprimă” → „Salvare ca PDF” sau butonul laboratorului „Descarcă PDF”.'
    };
  }
  if (u.startsWith('<!DOCTYPE') || u.startsWith('<HTML') || u.startsWith('<HEAD') || u.startsWith('<?XML')) {
    return {
      ok: false,
      cod: 'html',
      mesaj: 'Fișierul este pagină web (HTML), nu PDF. Salvează buletinul ca PDF din browser sau descarcă fișierul direct de pe site-ul laboratorului.'
    };
  }
  return {
    ok: false,
    cod: 'necunoscut',
    mesaj: 'Fișierul nu începe cu semnătura PDF (%PDF-). Probabil nu este un document PDF real; refă descărcarea de pe sursa originală.'
  };
}

async function selecteazaFisiere(files) {
  if (!files || !files.length) return;
  const pdfs = files.filter(f => f.name.toLowerCase().endsWith('.pdf'));
  const nonPdf = files.length - pdfs.length;
  if (!pdfs.length) {
    afiseazaMesaj('upload-out','eroare','Fișierele trebuie să fie PDF.');
    return;
  }
  const okList = [];
  const erori = [];
  for (const f of pdfs) {
    const v = await _verificaContinutPdfReal(f);
    if (v.ok) okList.push(f);
    else erori.push({ nume: f.name, mesaj: v.mesaj });
  }
  fisierSelectat = okList;
  if (!okList.length) {
    document.getElementById('file-name').innerHTML = erori.length === 1
      ? '📎 <span style="color:var(--rosu)">' + escHtml(erori[0].nume) + '</span>'
      : '📎 <span style="color:var(--rosu)">Niciun PDF valid</span>';
    document.getElementById('btn-upload').disabled = true;
    document.getElementById('btn-verificare').disabled = true;
    let html = '<div style="color:var(--rosu);font-size:0.88rem;line-height:1.45">';
    erori.forEach(e => {
      html += '<p style="margin:0 0 10px 0"><strong>' + escHtml(e.nume) + '</strong><br>' + escHtml(e.mesaj) + '</p>';
    });
    html += '</div>';
    afiseazaMesaj('upload-out','eroare', html);
    return;
  }
  const totalKB = okList.reduce((s, f) => s + f.size, 0) / 1024;
  let info = okList.length === 1
    ? '📎 ' + okList[0].name + ' (' + (okList[0].size/1024).toFixed(1) + ' KB)'
    : '📎 ' + okList.length + ' fișiere selectate (' + totalKB.toFixed(1) + ' KB total)';
  if (nonPdf > 0) info += ' · <span style="color:var(--rosu)">' + nonPdf + ' ignorate (nu sunt PDF)</span>';
  if (erori.length) {
    info += ' · <span style="color:var(--rosu)">' + erori.length + ' respinse (nu sunt PDF reale)</span>';
  }
  document.getElementById('file-name').innerHTML = info;
  document.getElementById('btn-upload').disabled = false;
  document.getElementById('btn-verificare').disabled = false;
  document.getElementById('btn-text').textContent = okList.length === 1 ? 'Procesează PDF' : 'Procesează ' + okList.length + ' PDF-uri';
  let outHtml = '';
  if (erori.length) {
    outHtml = '<div style="color:#a15a00;font-size:0.85rem;line-height:1.45;margin-bottom:8px"><strong>⚠ Unele fișiere au fost ignorate:</strong>';
    erori.forEach(e => {
      outHtml += '<p style="margin:8px 0 0 0"><strong>' + escHtml(e.nume) + '</strong><br>' + escHtml(e.mesaj) + '</p>';
    });
    outHtml += '</div>';
  }
  document.getElementById('upload-out').innerHTML = outHtml;
}

async function _uploadCuRetry(uploadUrl, fd) {
  let lastResp = null;
  let lastText = '';
  let lastErr = null;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const r = await fetch(uploadUrl, { method: 'POST', body: fd, headers: getAuthHeaders() });
      if (handle401(r)) return { aborted: true };
      const txt = await r.text();
      if (r.ok) return { response: r, text: txt };
      lastResp = r;
      lastText = txt;
      if ((r.status === 502 || r.status === 503 || r.status === 504) && attempt < 2) {
        await new Promise(res => setTimeout(res, 8000));
        continue;
      }
      break;
    } catch (err) {
      lastErr = err;
      if (attempt < 2) {
        await new Promise(res => setTimeout(res, 3000 * (attempt + 1)));
        continue;
      }
    }
  }
  if (!lastResp && lastErr) throw lastErr;
  return { response: lastResp, text: lastText };
}

async function _proceseazaUploadAsync(fd, onStatus) {
  const start = await _uploadCuRetry('/upload-async', fd);
  if (start.aborted) return { aborted: true };
  const rs = start.response;
  const txtStart = start.text || '';
  let jStart = {};
  try { jStart = JSON.parse(txtStart); } catch {}
  if (!rs || !rs.ok || !jStart.job_id) {
    return { response: rs, text: txtStart };
  }

  const jobId = String(jStart.job_id || '').trim();
  const t0 = Date.now();
  let lastStatus = 'queued';
  while ((Date.now() - t0) < 20 * 60 * 1000) {
    await new Promise(res => setTimeout(res, lastStatus === 'processing' ? 2500 : 1200));
    let rPoll;
    let txtPoll = '';
    try {
      rPoll = await fetch('/upload-async/' + encodeURIComponent(jobId), { headers: getAuthHeaders() });
      if (handle401(rPoll)) return { aborted: true };
      txtPoll = await rPoll.text();
    } catch {
      // Retry silent la probleme tranzitorii de retea/gateway.
      continue;
    }

    if (!rPoll.ok) {
      return { response: rPoll, text: txtPoll };
    }

    let jPoll = {};
    try { jPoll = JSON.parse(txtPoll); } catch {}
    lastStatus = String(jPoll.status || lastStatus);
    if (typeof onStatus === 'function') onStatus(lastStatus);

    if (lastStatus === 'success' || lastStatus === 'error') {
      const code = Number(jPoll.response_status || (lastStatus === 'success' ? 200 : 500));
      const payload = (jPoll && typeof jPoll.result === 'object' && jPoll.result !== null)
        ? jPoll.result
        : { detail: 'Job finalizat fara payload valid.' };
      return {
        response: { ok: code >= 200 && code < 400, status: code },
        text: JSON.stringify(payload),
      };
    }
  }

  return {
    response: { ok: false, status: 504 },
    text: JSON.stringify({
      detail: 'Procesarea dureaza prea mult pe server (timeout polling). Incearca din nou.',
    }),
  };
}

async function trimite(debugMode) {
  if (!fisierSelectat.length) return;
  const btn = document.getElementById('btn-upload');
  const btnText = document.getElementById('btn-text');
  const prog = document.getElementById('prog');
  const btnVerif = document.getElementById('btn-verificare');
  btn.disabled = true;
  if (btnVerif) btnVerif.disabled = true;
  const out = document.getElementById('upload-out');
  out.innerHTML = '';

  const total = fisierSelectat.length;
  let reusit = 0, esuat = 0;
  const rezultate = [];

  for (let i = 0; i < total; i++) {
    const f = fisierSelectat[i];
    btnText.innerHTML = '<span class="spinner"></span> ' + (i+1) + ' / ' + total + '…';
    prog.textContent = f.size > 500000
      ? f.name + ' – fișier mare, OCR poate dura câteva minute; nu închide pagina…'
      : f.name;

    const fd = new FormData();
    fd.append('file', f);
    const uploadUrl = '/upload' + (debugMode ? '?debug=1' : '?traceback=1');
    let status = 'ok', mesaj = '', pacientInfo = null;
    try {
      // Procesare asincronă pe /upload-async (job stocat în PostgreSQL, partajat între replici Railway).
      // Debug/Verificare folosesc /upload sincron (răspuns imediat cu diagnostic).
      const rq = debugMode
        ? await _uploadCuRetry(uploadUrl, fd)
        : await _proceseazaUploadAsync(fd, (st) => {
            if (st === 'processing') {
              prog.textContent = f.name + ' – se procesează pe server (OCR)…';
            } else if (st === 'queued') {
              prog.textContent = f.name + ' – în coadă de procesare…';
            }
          });
      if (rq.aborted) return;
      const r = rq.response;
      const txt = rq.text || '';
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
        if (j.debug) {
          pacientInfo = { cnp: j.cnp, nume: j.nume, prenume: j.prenume };
          mesaj = '[VERIFICARE] ' + escHtml(j.nume||'') + ' ' + escHtml(j.prenume||'')
            + ' · CNP: ' + escHtml(j.cnp||'')
            + (j.parser_version ? ' · <code style="font-size:0.75rem">' + escHtml(j.parser_version) + '</code>' : '')
            + ' · ' + (j.tip_extragere==='ocr'?'🔍 OCR':'📝 text') + (j.extractor ? ' (' + escHtml(j.extractor) + ')' : '')
            + ' · <strong>' + (j.numar_analize||0) + ' analize</strong>' + (j.lungime_text ? ' · ' + j.lungime_text + ' caractere' : '');
          if (j.triere_ai) {
            const t = j.triere_ai;
            const reasons = Array.isArray(t.reasons) && t.reasons.length ? (' · motive: ' + t.reasons.join(', ')) : '';
            mesaj += ' · Triage: <strong>' + escHtml(String((t.decision||'').toUpperCase())) + '</strong> (score=' + escHtml(String(t.score ?? 'n/a')) + ')' + escHtml(reasons);
          }
          if (j.analize && j.analize.length) {
            mesaj += '<br><details style="margin-top:8px"><summary style="cursor:pointer;font-size:0.85rem">Lista analize (' + j.analize.length + ')</summary><ul style="margin:8px 0 0 16px;font-size:0.82rem;max-height:200px;overflow-y:auto">'
              + j.analize.map(a => '<li>' + escHtml(a.denumire||'') + ' = ' + escHtml(String(a.valoare||'')) + ' ' + escHtml(a.unitate||'') + '</li>').join('')
              + '</ul></details>';
          }
          if (j.linii_0_80 && j.linii_0_80.length) {
            mesaj += '<br><details style="margin-top:6px"><summary style="cursor:pointer;font-size:0.8rem">Linii text extras (toate ' + j.linii_0_80.length + ') – pentru debug</summary><pre style="margin:6px 0 0;font-size:0.72rem;max-height:400px;overflow:auto;white-space:pre-wrap;background:var(--bg);padding:8px;border-radius:6px">' + escHtml((j.linii_0_80||[]).join('\n')) + '</pre></details>';
          }
          if (j.linii_excluse && j.linii_excluse.length) {
            mesaj += '<br><details style="margin-top:6px"><summary style="cursor:pointer;font-size:0.8rem;color:#c00">⚠ Linii EXCLUSE de parser (' + j.linii_excluse.length + ')</summary><pre style="margin:6px 0 0;font-size:0.72rem;max-height:300px;overflow:auto;white-space:pre-wrap;background:#fff0f0;padding:8px;border-radius:6px;color:#800">' + escHtml((j.linii_excluse||[]).join('\n')) + '</pre></details>';
          }
          if (j.text_primele_3000) {
            mesaj += '<br><details style="margin-top:6px"><summary style="cursor:pointer;font-size:0.8rem">Text extras (primele 6000 caractere)</summary><pre style="margin:6px 0 0;font-size:0.75rem;max-height:300px;overflow:auto;white-space:pre-wrap;background:var(--bg);padding:8px;border-radius:6px">' + escHtml(j.text_primele_3000) + '</pre></details>';
          }
          if (j.eroare) mesaj = '[EROARE] ' + escHtml(j.eroare) + (j.linii_0_80 && j.linii_0_80.length ? '<br><details style="margin-top:6px"><summary style="cursor:pointer;font-size:0.8rem">Linii text extras (' + j.linii_0_80.length + ')</summary><pre style="margin:6px 0 0;font-size:0.72rem;max-height:300px;overflow:auto;white-space:pre-wrap;background:var(--bg);padding:8px;border-radius:6px">' + escHtml((j.linii_0_80||[]).join('\n')) + '</pre></details>' : '');
        } else {
          pacientInfo = j.pacient || {};
          mesaj = 'Pacient: <strong>' + escHtml(pacientInfo.nume||'') + '</strong>'
            + ' (CNP: ' + escHtml(pacientInfo.cnp||'') + ')'
            + ' · ' + (j.tip_extragere==='ocr'?'🔍 OCR':'📝 text')
            + (j.extractor ? ' · ' + escHtml(j.extractor) : '')
            + ' · <strong>' + (j.numar_analize||0) + ' analize</strong>';
          if (j.triere_ai) {
            const t = j.triere_ai;
            const reasons = Array.isArray(t.reasons) && t.reasons.length ? (' · motive: ' + t.reasons.join(', ')) : '';
            mesaj += ' · Triage: <strong>' + escHtml(String((t.decision||'').toUpperCase())) + '</strong> (score=' + escHtml(String(t.score ?? 'n/a')) + ')' + escHtml(reasons);
          }
          const tAi = j.triere_ai;
          const dec = tAi ? String(tAi.decision || '').toLowerCase() : '';
          const scorN = tAi && typeof tAi.score === 'number' ? tAi.score : null;
          const afiseazaAvertScor = Boolean(j.ocr_calitate_slaba_salvata || (dec && dec !== 'auto') || (scorN !== null && scorN < 40));
          if (afiseazaAvertScor && tAi) {
            const recAi = (dec === 'ai' || (scorN !== null && scorN < 20) || j.ocr_calitate_slaba_salvata)
              ? ' <strong>Recomandăm verificarea cu AI</strong> sau corectarea manuală a analizelor marcate pentru revizuire.'
              : ' Recomandăm verificarea cu AI sau corectarea manuală înainte de a folosi valorile în clinică.';
            mesaj += '<div style="margin-top:8px;padding:9px 11px;border-radius:6px;background:#fff0f0;border:1px solid #f0b4b4;color:var(--rosu);font-size:0.84rem;line-height:1.35">'
              + '<strong>Scor document: ' + escHtml(String(tAi.score ?? '—')) + '/100</strong>'
              + (dec ? ' · triaj: <strong>' + escHtml(dec.toUpperCase()) + '</strong>' : '')
              + '. Calitate redusă sau multe analize de mapat.'
              + recAi
              + '</div>';
          }
          if (Array.isArray(j.warnings) && j.warnings.length) {
            mesaj += '<br><span style="font-size:0.8rem;color:#a15a00">' + escHtml(j.warnings.join(' | ')) + '</span>';
          }
        }
      } else {
        esuat++;
        status = 'err';
        mesaj = (j && j.detail) ? (Array.isArray(j.detail) ? j.detail.join(' ') : j.detail) : 'Eroare ' + r.status;
        if (j && j.triere_ai) {
          const t = j.triere_ai;
          const reasons = Array.isArray(t.reasons) && t.reasons.length ? (' · motive: ' + t.reasons.join(', ')) : '';
          mesaj += '<br><span style="font-size:0.8rem;color:#a15a00">Triage AI: <strong>' + escHtml(String((t.decision||'').toUpperCase())) + '</strong> (score=' + escHtml(String(t.score ?? 'n/a')) + ')' + escHtml(reasons) + '</span>';
        }
        if (j && j.traceback) {
          mesaj += '<br><details style="margin-top:6px"><summary style="cursor:pointer;font-size:0.8rem;color:var(--gri)">Traceback (debug)</summary><pre style="margin:6px 0 0;font-size:0.7rem;max-height:200px;overflow:auto;white-space:pre-wrap;background:#1e1e1e;color:#d4d4d4;padding:10px;border-radius:6px">' + escHtml(j.traceback) + '</pre></details>';
        }
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
  const bv = document.getElementById('btn-verificare');
  if (bv) bv.disabled = false;
  btnText.textContent = total === 1 ? 'Procesează PDF' : 'Procesează ' + total + ' PDF-uri';
  prog.textContent = '';
  // La verificare (debug), nu ștergem fișierele – utilizatorul poate da apoi Procesare pentru a salva
  if (!debugMode) {
    fisierSelectat = [];
    document.getElementById('file-name').innerHTML = '';
    fileInput.value = '';
  }
}

async function incarcaRecenti() {
  try {
    const r = await fetch('/pacienti?limit=50&offset=0', { headers: getAuthHeaders() });
    if (r.status === 401) { clearToken(); location.reload(); return; }
    const data = r.ok ? await r.json() : {};
    const lista = Array.isArray(data) ? data : (data.items || []);
    if (!lista.length) return;
    document.getElementById('card-pacienti-recenti').style.display = '';
    document.getElementById('lista-recenti').innerHTML =
      lista.map(p => `<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">
        <span><strong>${escHtml(p.nume||'')}</strong>${(p.prenume?' '+escHtml(p.prenume):'')} <span style="color:var(--gri);font-size:0.82rem">CNP: ${escHtml(p.cnp)}</span></span>
        <button class="btn btn-secondary" style="padding:6px 14px;font-size:0.8rem" onclick="veziPacient('${escHtml(p.cnp)}')">Vezi</button>
      </div>`).join('');
  } catch {}
}

// ─── Pacient ─────────────────────────────────────────────────────────────────
let _cautaPacientTimer = null;
const PLACEHOLDER_PACIENTI = '<p style="color:var(--gri);text-align:center;padding:24px;font-size:0.92rem">Se încarcă pacienții…</p>';

function afiseazaPlaceholderPacienti() {
  document.getElementById('lista-pacienti').innerHTML = PLACEHOLDER_PACIENTI;
}

const PAGINA_PACIENTI_LIMIT = 50;
let _paginaPacientiCurenta = 0;
let _totalPacienti = 0;
let _termenCautarePacienti = '';

function cautaPacient(q) {
  clearTimeout(_cautaPacientTimer);
  _cautaPacientTimer = setTimeout(() => { _paginaPacientiCurenta = 0; incarcaListaPacienti(q, 0); }, 320);
}

async function incarcaListaPacienti(q, pagina) {
  const el = document.getElementById('lista-pacienti');
  const termen = (q || '').trim();
  _termenCautarePacienti = termen;
  if (typeof pagina === 'number') _paginaPacientiCurenta = pagina;
  pagina = _paginaPacientiCurenta;
  el.innerHTML = '<span style="color:var(--gri);font-size:0.9rem">Se încarcă…</span>';
  try {
    const offset = pagina * PAGINA_PACIENTI_LIMIT;
    let url = '/pacienti?limit=' + PAGINA_PACIENTI_LIMIT + '&offset=' + offset;
    if (termen) url += '&q=' + encodeURIComponent(termen);
    const r = await fetch(url, { headers: getAuthHeaders() });
    if (handle401(r)) return;
    const data = r.ok ? await r.json() : {};
    const lista = Array.isArray(data) ? data : (data.items || []);
    const total = typeof data.total === 'number' ? data.total : lista.length;
    _totalPacienti = total;
    if (!lista.length) {
      el.innerHTML = '<p style="color:var(--gri);text-align:center;padding:20px">' +
        (termen ? 'Niciun pacient găsit.' : 'Niciun pacient în baza de date. Încarcă PDF-uri din tab-ul Upload.') + '</p>';
      return;
    }
    const nrB = n => n === 1 ? '1 buletin' : (n || 0) + ' buletine';
    const totalPagini = Math.ceil(total / PAGINA_PACIENTI_LIMIT) || 1;
    let html = '<div class="tabel-container"><table>' +
      '<thead><tr><th>Nume</th><th>CNP</th><th>Buletine</th><th>Acțiune</th></tr></thead><tbody>' +
      lista.map(p => `<tr>
        <td><strong>${escHtml(p.nume||'')}</strong>${p.prenume?' '+escHtml(p.prenume):''}</td>
        <td style="font-family:monospace;font-size:0.9rem">${escHtml(p.cnp)}</td>
        <td><span class="badge badge-norm" style="cursor:default">${nrB(p.nr_buletine)}</span></td>
        <td style="white-space:nowrap">
          <button class="btn btn-secondary" style="padding:6px 14px;font-size:0.82rem" onclick="veziPacient('${escHtml(p.cnp)}')" title="Vezi analize">👤 Analize</button>
          <button class="btn-sterge-pacient" data-id="${p.id}" data-nume="${escHtml((p.nume||'')+(p.prenume?' '+p.prenume:''))}" data-cnp="${escHtml(p.cnp)}" onclick="stergePacientDinListaEl(this)" title="Șterge pacient" style="margin-left:4px">✕</button>
        </td>
      </tr>`).join('') +
      '</tbody></table></div>';
    if (totalPagini > 1) {
      html += '<div class="paginare-pacienti" style="display:flex;align-items:center;justify-content:center;gap:12px;margin-top:16px;flex-wrap:wrap">' +
        '<span style="color:var(--gri);font-size:0.88rem">Pagina ' + (pagina + 1) + ' din ' + totalPagini + ' (' + total + ' pacienți)</span>' +
        '<button class="btn btn-secondary" ' + (pagina <= 0 ? 'disabled' : 'onclick="incarcaListaPacienti(_termenCautarePacienti, ' + (pagina - 1) + ')"') + ' style="padding:6px 14px;font-size:0.85rem">← Înapoi</button>' +
        '<button class="btn btn-secondary" ' + (pagina >= totalPagini - 1 ? 'disabled' : 'onclick="incarcaListaPacienti(_termenCautarePacienti, ' + (pagina + 1) + ')"') + ' style="padding:6px 14px;font-size:0.85rem">Înainte →</button>' +
        '</div>';
    }
    el.innerHTML = html;
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

  // Anuleaza fetch-ul anterior (evita race: click A -> B -> răspuns A suprascrie B)
  _veziPacientAbortController?.abort();
  _veziPacientAbortController = new AbortController();
  const signal = _veziPacientAbortController.signal;

  // Arata placeholder in tab dinamic temporar
  const numeTemporar = cnp;
  deschideTabPacient(cnp, numeTemporar,
    '<div class="card"><p style="color:var(--gri)">Se încarcă datele pacientului…</p></div>');

  try {
    const r = await fetch('/pacient/' + encodeURIComponent(String(cnp)) + '/evolutie-matrice', { headers: getAuthHeaders(), signal });
    if (handle401(r)) return;
    if (!r.ok) {
      deschideTabPacient(cnp, cnp,
        '<div class="card"><p style="color:red">Pacientul nu a fost găsit.</p></div>');
      return;
    }

    const data = await r.json();
    const numePacient = (data.pacient.nume||'') + (data.pacient.prenume ? ' ' + data.pacient.prenume : '');
    const initiale = (data.pacient.nume||'?').substring(0,1);

    // Header pacient (cu buton Editează nume pentru corectie nume corupte)
    const numePrenumeJson = JSON.stringify({n: data.pacient.nume||'', p: data.pacient.prenume||''}).replace(/'/g,'&#39;');
    let html = `<div class="card">
      <div class="pacient-header">
        <div class="pacient-avatar">${escHtml(initiale)}</div>
        <div class="pacient-info">
          <h3>${escHtml(data.pacient.nume||'')}${data.pacient.prenume?' '+escHtml(data.pacient.prenume):''}
            <button data-cnp="${escHtml(cnp)}" data-pacient='${numePrenumeJson}' onclick="editeazaNumePacient(this)" title="Editează nume (ex: corectie TGO ASAT)"
              style="background:none;border:none;cursor:pointer;color:var(--albastru);font-size:0.75rem;padding:2px 6px;margin-left:6px">✏️</button>
          </h3>
          <p>CNP: <strong style="font-family:monospace">${escHtml(data.pacient.cnp)}</strong></p>
          <p>Buletine: <strong>${data.date_buletine.length}</strong> &nbsp;|&nbsp; Analize: <strong>${typeof data.rezultate_in_baza === 'number' ? data.rezultate_in_baza : data.analize.length}</strong>${typeof data.rezultate_in_baza === 'number' && data.rezultate_in_baza !== data.analize.length ? ' <span style="font-size:0.78rem;color:var(--gri)" title="Rânduri distincte în tabel (grupare)">(' + data.analize.length + ' rânduri)</span>' : ''}</p>
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

    // Rânduri analize cu separatoare de categorie
    let categorieCurenta = null;
    data.analize.forEach(a => {
      // Separator de categorie
      const catAfisata = a.categorie || '';
      if (catAfisata && catAfisata !== categorieCurenta) {
        categorieCurenta = catAfisata;
        const nrColoane = data.date_buletine.length + 1;
        html += `<tr class="sectiune-separator"><td colspan="${nrColoane}" class="sectiune-header">${escHtml(catAfisata)}</td></tr>`;
      }

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
    if (e.name === 'AbortError') return;
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
    const v = rz.analiza_standard_id ?? '';
    const selOpts = opts.replace(`value="${v}"`, `value="${v}" selected`);
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
              style="display:none;position:fixed;z-index:99999;background:white;border:1.5px solid #1a73e8;border-radius:6px;box-shadow:0 6px 24px rgba(0,0,0,0.2);max-height:350px;overflow-y:auto;min-width:320px">
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
      const j = await r.json().catch(() => ({}));
      if (row) {
        row.style.background = '#e8f5e9';
        setTimeout(() => { if(row) row.style.background = ''; }, 1200);
      }
      if (j.alias_salvat) {
        showEditMsg('✅ Salvat. Sistemul a învățat această asociație și o va recunoaște automat la upload-uri viitoare.', false);
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
  const searchInput = document.getElementById('new-analiza-search');
  if (!dropdown || !searchInput) return;
  // Pozitioneaza dropdown fix sub input
  const rect = searchInput.getBoundingClientRect();
  dropdown.style.left = rect.left + 'px';
  dropdown.style.top = (rect.bottom + 2) + 'px';
  dropdown.style.width = rect.width + 'px';
  const q = query.trim().toLowerCase();
  const lista = _analizeLista || [];

  const filtrate = q.length === 0
    ? lista
    : lista.filter(a => {
        const den = (a.denumire_standard || '').toLowerCase();
        const cod = (a.cod_standard || '').toLowerCase();
        return den.includes(q) || cod.includes(q);
      });

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

function stergePacientDinListaEl(btn) {
  const id = btn.getAttribute('data-id');
  const nume = btn.getAttribute('data-nume') || '';
  const cnp = btn.getAttribute('data-cnp') || '';
  stergePacientDinLista(parseInt(id), nume, cnp);
}
async function stergePacientDinLista(pacientId, numePacient, cnp) {
  if (!confirm('Ștergi pacientul "' + numePacient + '" cu TOATE buletinele și analizele lui? Acțiunea nu poate fi anulată!')) return;
  try {
    const r = await fetch('/pacient/' + pacientId, { method: 'DELETE', headers: getAuthHeaders() });
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      if (_tabPacienti[cnp]) inchideTabPacient(cnp);
      incarcaListaPacienti(document.getElementById('q-pacient')?.value || '');
    } else {
      alert('Eroare: ' + (j.detail || 'Nu s-a putut șterge pacientul.'));
    }
  } catch(e) {
    alert('Eroare: ' + e.message);
  }
}

async function editeazaNumePacient(btn) {
  const cnp = btn.getAttribute('data-cnp');
  let dat = {n:'', p:''};
  try { dat = JSON.parse(btn.getAttribute('data-pacient')||'{}'); } catch {}
  const n = prompt('Nume pacient (ex: POPESCU):', dat.n || '');
  if (n === null) return;
  const p = prompt('Prenume (optional, Enter pt gol):', dat.p || '');
  if (p === null) return;
  try {
    const r = await fetch('/pacient/' + encodeURIComponent(cnp), {
      method: 'PATCH',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ nume: n.trim(), prenume: (p||'').trim() || null })
    });
    if (handle401(r)) return;
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      delete _tabPacienti[cnp];
      await veziPacient(cnp);
    } else {
      alert('Eroare: ' + (j.detail || r.status));
    }
  } catch(e) {
    alert('Eroare: ' + e.message);
  }
}

async function stergePacient(pacientId, numePacient, cnp) {
  if (!confirm('Ștergi pacientul "' + numePacient + '" cu TOATE buletinele și analizele lui? Acțiunea nu poate fi anulată!')) return;
  try {
    const r = await fetch('/pacient/' + pacientId, { method: 'DELETE', headers: getAuthHeaders() });
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      inchideTabPacient(cnp);
      incarcaListaPacienti(document.getElementById('q-pacient')?.value || '');
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
    const r = await fetch('/pacienti?q=' + encodeURIComponent(q.trim()) + '&limit=100&offset=0', { headers: getAuthHeaders() });
    const data = await r.json();
    const lista = Array.isArray(data) ? data : (data.items || []);
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

// ─── Tab 3b: Gestionare analize standard ─────────────────────────────────────
let _analize_std_toate = [];

async function incarcaAnalizeleStandard() {
  const r = await fetch('/analize-standard', { headers: getAuthHeaders() });
  const lista = await r.json();
  _analize_std_toate = lista;
  document.getElementById('cnt-std').textContent = lista.length;
  afiseazaListaStd(lista);
}

function filtreazaStd(q) {
  const qlow = q.trim().toLowerCase();
  const filtrate = qlow
    ? _analize_std_toate.filter(a =>
        (a.denumire_standard || '').toLowerCase().includes(qlow) ||
        (a.cod_standard || '').toLowerCase().includes(qlow))
    : _analize_std_toate;
  afiseazaListaStd(filtrate);
}

function afiseazaListaStd(lista) {
  const el = document.getElementById('lista-std');
  if (!lista.length) {
    el.innerHTML = '<p style="padding:12px;color:var(--gri)">Niciun rezultat.</p>';
    return;
  }
  el.innerHTML = lista.map(a =>
    '<div style="padding:7px 12px;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;font-size:0.85rem">' +
    '<span>' + escHtml(a.denumire_standard) + '</span>' +
    '<span style="color:#999;font-family:monospace">' + escHtml(a.cod_standard) + '</span>' +
    '</div>'
  ).join('');
}

async function adaugaAnalizaStandard() {
  const denumire = document.getElementById('new-std-denumire').value.trim();
  const cod = document.getElementById('new-std-cod').value.trim().toUpperCase();
  const msg = document.getElementById('msg-new-std');
  if (!denumire || !cod) {
    msg.textContent = 'Completează denumirea și codul.';
    msg.style.color = 'var(--rosu)';
    return;
  }
  const r = await fetch('/analize-standard', {
    method: 'POST',
    headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ denumire, cod })
  });
  const j = await r.json();
  if (r.ok) {
    msg.textContent = 'Adăugat: ' + j.denumire_standard + ' (' + j.cod_standard + ')';
    msg.style.color = 'var(--verde)';
    document.getElementById('new-std-denumire').value = '';
    document.getElementById('new-std-cod').value = '';
    await incarcaAnalizeleStandard();
    // Reincarca si lista din dropdown editare
    _analizeLista = null;
    incarcaAnalizeLista();
  } else {
    msg.textContent = j.detail || 'Eroare.';
    msg.style.color = 'var(--rosu)';
  }
  setTimeout(() => { msg.textContent = ''; }, 4000);
}

// ─── Tab 4: Analize necunoscute ───────────────────────────────────────────────
let _analize_std_cache = null;

/** Aliniat la backend.analiza_categorii.potrivire_categorie_pdf_cu_grup (etichete categorie_grup). */
function potrivireCategoriePdfCuGrupJs(categoriePdf, categorieGrup) {
  const g = String(categorieGrup || '').toLowerCase();
  if (!categoriePdf || !String(categoriePdf).trim()) return true;
  const p = String(categoriePdf).trim().toLowerCase();
  if (p.includes('hemo') || p.includes('leuco') || p.includes('formula') || p.includes('hemat'))
    return g.includes('hemoleuco') || g.includes('hemat');
  if (p.includes('urin') || p.includes('sediment') || p.includes('sumar'))
    return g.includes('urin');
  if (p.includes('biochim') || p.includes('lipid'))
    return g.includes('biochim') || g.includes('metabol');
  if (p.includes('microbio') || p.includes('cultur') || p.includes('infec') || p.includes('bacterio'))
    return g.includes('microbiol') || g.includes('infec');
  if (p.includes('imun') || p.includes('serol'))
    return g.includes('imun') || g.includes('serol');
  if (p.includes('hormon') || p.includes('tiroid') || p.includes('endocrin'))
    return g.includes('hormon') || g.includes('tiroid');
  if (p.includes('coagul') || p.includes('hemost'))
    return g.includes('coagul') || g.includes('hemost');
  if (p.includes('marker') || p.includes('tumor') || p.includes('onco'))
    return g.includes('marker') || g.includes('tumor');
  if (p.includes('miner') || p.includes('electrol'))
    return g.includes('miner') || g.includes('oligoe');
  if (p.includes('inflam'))
    return g.includes('biochim');
  if (p.includes('electroforez'))
    return g.includes('alte') || g.includes('biochim');
  return true;
}

function buildStdSelectOptionsHtml(stdList, categoriePdf) {
  const opt = (s) => `<option value="${s.id}">${escHtml(s.denumire_standard)} (${escHtml(s.cod_standard)})</option>`;
  const cat = (categoriePdf || '').trim();
  if (!cat) {
    return '<option value="">— Selectați —</option>' + stdList.map(opt).join('');
  }
  const matched = stdList.filter(s => potrivireCategoriePdfCuGrupJs(cat, s.categorie_grup));
  const rest = stdList.filter(s => !potrivireCategoriePdfCuGrupJs(cat, s.categorie_grup));
  let h = '<option value="">— Selectați —</option>';
  if (matched.length) {
    h += '<optgroup label="Potrivite cu secțiunea din PDF">' + matched.map(opt).join('') + '</optgroup>';
  }
  h += '<optgroup label="Toate celelalte analize">' + rest.map(opt).join('') + '</optgroup>';
  return h;
}

async function incarcaStandardeCache() {
  if (_analize_std_cache && _analize_std_cache.length && _analize_std_cache[0].categorie_grup === undefined)
    _analize_std_cache = null;
  if (_analize_std_cache) return _analize_std_cache;
  try {
    const r = await fetch('/analize-standard', { headers: getAuthHeaders() });
    _analize_std_cache = await r.json();
  } catch { _analize_std_cache = []; }
  return _analize_std_cache;
}

async function golesteAnalizeAsociate() {
  if (!confirm('Sigur ștergeți TOATE analizele necunoscute și alias-urile (asocierile)? Nu se poate reveni.')) return;
  try {
    const r = await fetch('/goleste-analize-asociate', { method: 'POST', headers: getAuthHeaders() });
    const j = await r.json();
    if (r.ok && j.ok) {
      document.getElementById('badge-nec').style.display = 'none';
      incarcaNecunoscute();
      alert(j.mesaj || 'Toate asocierile au fost șterse.');
    } else {
      alert('Eroare: ' + (j.detail || 'Necunoscut'));
    }
  } catch (e) {
    alert('Eroare: ' + e.message);
  }
}

async function incarcaNecunoscute() {
  const el = document.getElementById('lista-necunoscute');
  el.innerHTML = '<p style="color:var(--gri)">Se încarcă…</p>';
  try {
    const rNec = await fetch('/analize-necunoscute', { headers: getAuthHeaders() });
    if (handle401(rNec)) return;
    const nec = rNec.ok ? await rNec.json() : [];
    const std = await incarcaStandardeCache();

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
      const bulkSel = document.getElementById('sel-std-bulk');
      if (bulkSel) bulkSel.innerHTML = '<option value="">— Analiză standard —</option>';
      updateNecBulkCount();
      return;
    }

    const bulkSel = document.getElementById('sel-std-bulk');
    if (bulkSel) bulkSel.innerHTML = buildStdSelectOptionsHtml(std, null);

    el.innerHTML = `
      <p style="font-size:0.85rem;color:var(--gri);margin-bottom:12px">
        ${nec.length} analize nerecunoscute. Lista e grupată după <strong>secțiunea din buletin</strong> (Hemoleucogramă, Biochimie, Urină…).
        În dropdown, analizele standard <em>potrivite secțiunii</em> apar primele (optgroup).
      </p>
      <div class="tabel-container"><table>
      <thead><tr>
        <th style="width:40px;text-align:center" title="Selectare pentru aprobare în masă">
          <input type="checkbox" id="nec-select-all" aria-label="Bifează toate" onchange="toggleSelectAllNec(this)">
        </th>
        <th>Secțiune PDF</th>
        <th>Denumire din PDF</th>
        <th>Apariții</th>
        <th>Asociază cu analiza standard</th>
        <th>Acțiuni</th>
      </tr></thead>
      <tbody>` +
      nec.map(n => {
        const catPdf = (n.categorie || '').trim();
        const catBadge = catPdf
          ? `<span class="badge badge-norm" title="Categorie extrasă la parsare din buletin" style="max-width:160px;display:inline-block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(catPdf)}</span>`
          : '<span style="color:var(--gri);font-size:0.8rem" title="Reîncărcați după upload-uri noi sau lipsă secțiune în PDF">—</span>';
        const opts = buildStdSelectOptionsHtml(std, n.categorie);
        return `<tr id="nec-row-${n.id}">
        <td style="vertical-align:middle;text-align:center">
          <input type="checkbox" class="nec-cb" data-id="${n.id}" onchange="updateNecBulkCount()" aria-label="Selectează rând">
        </td>
        <td style="vertical-align:top">${catBadge}</td>
        <td>
          <strong>${escHtml(n.denumire_raw)}</strong>
          <div style="font-size:0.75rem;color:var(--gri);margin-top:2px">Prima apariție: ${(n.created_at||'').substring(0,10)}</div>
        </td>
        <td><span class="badge badge-norm">${n.aparitii}×</span></td>
        <td>
          <select id="sel-std-${n.id}" style="width:100%;padding:6px 10px;border:1px solid var(--border);border-radius:6px;font-size:0.85rem">
            ${opts}
          </select>
        </td>
        <td style="white-space:nowrap">
          <button class="btn btn-primary" style="padding:6px 12px;font-size:0.82rem;margin-right:4px"
            onclick="aprobaAlias(${n.id})">✓ Asociază</button>
          <button class="btn btn-secondary" style="padding:6px 10px;font-size:0.82rem"
            title="Șterge (zgomot / artefact OCR)"
            onclick="stergeNecunoscuta(${n.id})">🗑</button>
        </td>
      </tr>`;
      }).join('') +
      '</tbody></table></div>';
    updateNecBulkCount();
    const sa = document.getElementById('nec-select-all');
    if (sa) sa.checked = false;

  } catch(e) {
    el.innerHTML = '<p style="color:red">Eroare: ' + e.message + '</p>';
  }
}

function toggleSelectAllNec(cb) {
  document.querySelectorAll('.nec-cb').forEach(x => { x.checked = cb.checked; });
  updateNecBulkCount();
}

function updateNecBulkCount() {
  const n = document.querySelectorAll('.nec-cb:checked').length;
  const el = document.getElementById('nec-bulk-count');
  if (el) el.textContent = n + ' selectat' + (n === 1 ? '' : 'e');
}

async function aprobaAlias(id) {
  const sel = document.getElementById('sel-std-' + id);
  const aid = sel ? sel.value : '';
  if (!aid) { alert('Selectați mai întâi analiza standard!'); return; }

  try {
    const r = await fetch('/aproba-alias', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ necunoscuta_id: id, analiza_standard_id: parseInt(aid, 10) })
    });
    const j = await r.json();
    if (r.ok) {
      const row = document.getElementById('nec-row-' + id);
      if (row) {
        row.innerHTML = `<td colspan="6">
          <span style="color:var(--verde)">✅ Asociere reușită. Rezultatele existente au fost actualizate; la următorul upload recunoașterea va fi automată.</span>
        </td>`;
      }
      // Invalideaza cache alias pe toate workerii (Railway multi-worker)
      fetch('/invalideaza-cache-alias', { method: 'POST', headers: getAuthHeaders() }).catch(() => {});
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

async function aprobaAliasBulk() {
  const ids = Array.from(document.querySelectorAll('.nec-cb:checked'))
    .map(c => parseInt(c.getAttribute('data-id'), 10))
    .filter(x => !isNaN(x) && x > 0);
  const bulkSel = document.getElementById('sel-std-bulk');
  const aid = bulkSel ? bulkSel.value : '';
  if (!ids.length) {
    alert('Bifați cel puțin un rând din tabel.');
    return;
  }
  if (!aid) {
    alert('Selectați analiza standard în zona „Aprobare în masă”.');
    return;
  }
  if (!confirm('Asociați ' + ids.length + ' denumiri la analiza aleasă? Se creează aliasuri și se actualizează retroactiv rezultatele nemapate (ca la un singur click).')) {
    return;
  }
  try {
    const r = await fetch('/aproba-alias-bulk', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ necunoscuta_ids: ids, analiza_standard_id: parseInt(aid, 10) })
    });
    const j = await r.json();
    if (r.ok) {
      let msg = j.mesaj || 'Gata.';
      if (j.skipped_ids && j.skipped_ids.length) {
        msg += ' (Id-uri ignorate: ' + j.skipped_ids.join(', ') + ')';
      }
      fetch('/invalideaza-cache-alias', { method: 'POST', headers: getAuthHeaders() }).catch(() => {});
      await incarcaNecunoscute();
      alert(msg);
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

// incarcaRecenti si badge analize-necunoscute se apeleaza din checkAuth() dupa login
</script>

</div><!-- /app-container -->
</body>
</html>"""
    return html


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
