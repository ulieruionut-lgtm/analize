"""Router admin: migrari DB, backup/restore, import dictionar, stergeri."""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from backend.config import settings
from backend.database import (
    backfill_categorie_necunoscuta_din_rezultate,
    delete_buletin,
    delete_pacient,
    export_backup_data,
    restore_from_backup,
)
from backend.deps import _is_admin, get_current_user, postgresql_connect

router = APIRouter()


class BackfillNecunoscutaCategorieBody(BaseModel):
    """Backfill categorie (sectiune PDF) pentru analiza_necunoscuta din rezultate_analize."""
    dry_run: bool = True
    limit: Optional[int] = None


@router.get("/api/migrate")
@router.post("/api/migrate")
async def run_migrations():
    """Rulează migrările PostgreSQL dacă tabelele lipsesc. Accesează în browser pentru setup inițial."""
    url = (settings.database_url or "").strip()
    if not url or not url.lower().startswith("postgresql"):
        return {"ok": False, "detail": "Nu folosești PostgreSQL."}
    try:
        sql_dir = Path(__file__).resolve().parent.parent.parent / "sql"
        conn = postgresql_connect(url)
        conn.autocommit = False
        done = []
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'pacienti'")
            if cur.fetchone() is None:
                initial_files = [
                    "001_schema.sql", "003_users_auth_postgres.sql",
                    "004_pg_analize_extinse.sql", "005_pg_alias_fix.sql",
                    "006_pg_alias_ocr.sql", "007_ordine_categorie.sql",
                    "008_pg_alias_bioclinica.sql", "009_pg_laboratoare_catalog.sql",
                    "010_pg_alias_laboratoare.sql",
                ]
                for fname in initial_files:
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
                upgrade_files = [
                    "007_ordine_categorie.sql", "008_pg_alias_bioclinica.sql",
                    "009_pg_laboratoare_catalog.sql", "010_pg_alias_laboratoare.sql",
                    "011_pg_valoare_text.sql", "012_pg_necunoscuta_categorie.sql",
                    "014_pg_rezultat_meta.sql", "015_pg_alias_clinice_necunoscute.sql",
                    "016_pg_pacienti_perf.sql", "017_pg_upload_async_jobs.sql",
                    "018_pg_indexes.sql", "019_pg_medlife_pdr_aliases.sql",
                    "020_pg_urina_params.sql", "021_pg_teo_health_aliases.sql",
                    "022_pg_teo_health_aliases2.sql", "023_pg_sediment_urina.sql",
                    "024_pg_teo_health_sediment2.sql", "025_pg_necunoscuta_laborator.sql",
                    "026_pg_medlife_uroculture_text.sql",
                ]
                for fname in upgrade_files:
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


@router.get("/api/fix-schema")
@router.post("/api/fix-schema")
async def fix_schema():
    """Adaugă coloanele lipsă direct (ALTER TABLE IF NOT EXISTS)."""
    url = (settings.database_url or "").strip()
    if not url or not url.lower().startswith("postgresql"):
        return {"ok": False, "detail": "Nu folosești PostgreSQL."}
    fixes = [
        ("rezultat_meta", "ALTER TABLE rezultate_analize ADD COLUMN IF NOT EXISTS rezultat_meta TEXT"),
        ("necunoscuta_categorie", "ALTER TABLE analize_necunoscute ADD COLUMN IF NOT EXISTS categorie TEXT"),
    ]
    done, errors = [], []
    try:
        conn = postgresql_connect(url)
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


@router.get("/api/backup")
async def backup_export(current_user: dict = Depends(get_current_user)):
    """Export backup baza de analize (JSON). Doar admin."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Doar admin poate descarca backup-ul.")
    try:
        data = export_backup_data()
        ts = data.get("exported_at", "")[:19].replace("-", "").replace("T", "_").replace(":", "")
        filename = (
            f"analize_backup_{ts}.json"
            if ts
            else "analize_backup_" + datetime.utcnow().strftime("%Y%m%d_%H%M") + ".json"
        )
        body = json.dumps(data, ensure_ascii=False, indent=2)
        return StreamingResponse(
            iter([body.encode("utf-8")]),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Eroare la export: {str(e)}"})


@router.post("/api/restore")
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
        return JSONResponse(status_code=500, content={"detail": f"Eroare la import: {str(e)}"})


@router.post("/api/import-dictionar-excel")
async def import_dictionar_excel(
    file: UploadFile = File(None),
    current_user: dict = Depends(get_current_user),
):
    """Importă dictionar analize + aliasuri din Excel. Doar admin."""
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Doar admin.")
    try:
        from backend.import_dictionar import import_dictionar_excel as _do_import
        root = Path(__file__).resolve().parent.parent.parent
        xlsx_path = root / "dictionar_analize_300_1200_alias.xlsx"
        if file and file.filename and file.filename.lower().endswith(".xlsx"):
            source = await file.read()
        elif xlsx_path.exists():
            source = xlsx_path
        else:
            raise HTTPException(
                status_code=400,
                detail="Încarcă fișierul Excel sau pune dictionar_analize_300_1200_alias.xlsx în rădăcina proiectului.",
            )
        rez = _do_import(source)
        if not rez.get("ok"):
            raise HTTPException(status_code=500, detail=rez.get("mesaj", "Eroare import"))
        return rez
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.post("/api/admin/backfill-necunoscuta-categorie")
async def admin_backfill_necunoscuta_categorie(
    body: BackfillNecunoscutaCategorieBody,
    current_user: dict = Depends(get_current_user),
):
    """
    Completează analiza_necunoscuta.categorie din rezultate.
    Implicit dry_run=true (simulare). Doar utilizatorul admin.
    """
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Doar admin poate rula această operație.")
    try:
        return backfill_categorie_necunoscuta_din_rezultate(dry_run=body.dry_run, limit=body.limit)
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.delete("/buletin/{buletin_id}")
async def sterge_buletin(buletin_id: int, current_user: dict = Depends(get_current_user)):
    """Sterge un buletin (cu toate analizele din el)."""
    ok = delete_buletin(buletin_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Buletinul nu a fost găsit.")
    return {"message": "Buletin șters."}


@router.delete("/pacient/{pacient_id}")
async def sterge_pacient(pacient_id: int, current_user: dict = Depends(get_current_user)):
    """Sterge un pacient cu toate buletinele si analizele lui."""
    ok = delete_pacient(pacient_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Pacientul nu a fost găsit.")
    return {"message": "Pacient șters complet."}
