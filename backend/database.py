"""Conexiune SQLite (implicit), PostgreSQL sau MySQL. CRUD pentru MVP."""
import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import settings

_USE_SQLITE = None
_DB_TYPE = None  # 'sqlite', 'postgresql', 'mysql'

def _detect_db_type() -> str:
    """Detectează tipul de bază de date din DATABASE_URL."""
    global _DB_TYPE
    if _DB_TYPE is None:
        url = (settings.database_url or "").strip().lower()
        if not url or url.startswith("sqlite") or url.endswith(".db"):
            _DB_TYPE = "sqlite"
        elif url.startswith("mysql") or url.startswith("mysql+pymysql"):
            _DB_TYPE = "mysql"
        elif url.startswith("postgres"):
            _DB_TYPE = "postgresql"
        else:
            _DB_TYPE = "sqlite"  # fallback
    return _DB_TYPE

def _use_sqlite() -> bool:
    global _USE_SQLITE
    if _USE_SQLITE is None:
        _USE_SQLITE = _detect_db_type() == "sqlite"
    return _USE_SQLITE


def _sqlite_path() -> Path:
    p = getattr(settings, "db_path", None) or (Path(__file__).resolve().parent.parent / "analize.db")
    return p


_SQLITE_INIT_DONE = False


def _init_sqlite_if_needed():
    """Creează tabelele și datele inițiale dacă baza e goală (ca să meargă fără run_migrations)."""
    global _SQLITE_INIT_DONE
    if _SQLITE_INIT_DONE:
        return
    path = _sqlite_path()
    root = path.parent
    sql_dir = root / "sql"
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pacienti'")
        if cur.fetchone():
            _SQLITE_INIT_DONE = True
            return
        for fname in [
            "schema_sqlite.sql",
            "seed_sqlite.sql",
            "002_analize_extinse.sql",
            "009_laboratoare_catalog.sql",
            "015_alias_clinice_necunoscute.sql",
        ]:
            fpath = sql_dir / fname
            if fpath.exists():
                conn.executescript(fpath.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
    _SQLITE_INIT_DONE = True


def get_connection():
    db_type = _detect_db_type()
    
    if db_type == "sqlite":
        _init_sqlite_if_needed()
        conn = sqlite3.connect(str(_sqlite_path()))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    elif db_type == "mysql":
        import pymysql
        import pymysql.cursors
        # Convertim URL-ul MySQL pentru pymysql
        # mysql://user:pass@host:port/database -> params
        url = settings.database_url
        # Simplu: folosim direct pymysql cu URL
        return pymysql.connect(
            host=url.split("@")[1].split(":")[0] if "@" in url else "localhost",
            user=url.split("//")[1].split(":")[0] if "//" in url and ":" in url else "root",
            password=url.split(":")[2].split("@")[0] if url.count(":") >= 2 else "",
            database=url.split("/")[-1] if "/" in url else "analize",
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4'
        )
    
    else:  # postgresql
        import psycopg2
        from psycopg2.extras import RealDictCursor
        return psycopg2.connect(
            settings.database_url,
            cursor_factory=RealDictCursor,
        )


@contextmanager
def get_cursor(commit: bool = True):
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    finally:
        cur.close()
        conn.close()


def _fetchone_dict(cur) -> Optional[dict]:
    """Converteste fetchone() la dict, sigur pentru orice tip de row (tuple, RealDictRow, etc.)."""
    row = cur.fetchone()
    if row is None:
        return None
    try:
        if hasattr(row, "keys"):
            return dict(row)
        if cur.description and hasattr(row, "__getitem__"):
            cols = [c[0] for c in cur.description]
            return dict(zip(cols, row))
    except (IndexError, TypeError, KeyError):
        pass
    return {}


def _row_get(row, key_or_index, default=None):
    """Extrage o valoare din row - sigur pentru dict (PostgreSQL) si tuple (fallback)."""
    if row is None:
        return default
    try:
        if hasattr(row, "keys"):
            if isinstance(key_or_index, str):
                return row.get(key_or_index, default)
            if isinstance(key_or_index, int):
                keys = list(row.keys())
                if 0 <= key_or_index < len(keys):
                    return row.get(keys[key_or_index], default)
                return default
        if isinstance(key_or_index, int) and hasattr(row, "__getitem__"):
            if 0 <= key_or_index < len(row):
                return row[key_or_index]
            return default
    except (IndexError, KeyError, TypeError):
        pass
    return default


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    try:
        if not hasattr(row, "keys"):
            return {}
        d = dict(row)
        for k, v in list(d.items()):
            if isinstance(v, (datetime, date)):
                d[k] = v.isoformat()
        return d
    except (IndexError, TypeError, KeyError, AttributeError):
        return {}


# --- Pacienti ---
# Nume considerate invalide/corupte - la upload nou, NU le suprascriem pe cele deja valide
def _nume_invalid(nume: Optional[str]) -> bool:
    """Returneaza True daca numele e corupt sau necunoscut (se poate inlocui la upload)."""
    import re
    if not nume or not str(nume).strip():
        return True
    s = str(nume).strip()
    if s == "Necunoscut":
        return True
    if len(s) > 80:
        return True
    low = s.lower()
    if any(x in low for x in (
        "medic", "varsta", "pacient", "nume pacient", "beneficiar", "cod client",
        "data inregistrari", "data inregistrare", "data tipar",
        "trimitator", "medicitrimitator",
        "materno-fetala", "materno fetala", "rejuvenare vaginala",
    )):
        return True
    # Dublare OCR de prenume/sintagma la final: "X Y Z Y Z"
    toks = re.split(r"\s+", s)
    if len(toks) >= 5:
        rest = toks[1:]
        if len(rest) % 2 == 0:
            h = len(rest) // 2
            if [x.lower() for x in rest[:h]] == [x.lower() for x in rest[h:]]:
                return True
    # Nume care incep cu apostrof parazit
    if re.match(r"^['\u2018\u2019\u201c\u201d\"]", s):
        return True
    # Secvente repetitive (ex: "MATEI M, 1 MATEI M, 1")
    if re.search(r"\s+[MF]\s*,\s*\d+\s+", s):
        return True
    # Nume tip analiză (ex: "TGO (ASAT)", "CRP (mg/L)") – parser OCR confundă uneori
    if re.match(r"^[A-Za-z0-9]{2,20}\s*\([A-Za-z0-9/]+\)$", s, re.IGNORECASE):
        return True
    return False


def _sterge_prenume_corupt_la_reupload(
    prenume_nou: Optional[str], prenume_vechi: Optional[str],
) -> bool:
    """
    Dacă noul buletin nu aduce prenume dar vechiul din DB e corupt (ex. «CNP: CNP:»),
    returnează True → apelantul golește câmpul (parserul corect nu mai trimite gunoi).
    """
    if (prenume_nou or "").strip():
        return False
    ov = (prenume_vechi or "").strip()
    if not ov:
        return False
    try:
        from backend.parser import _curata_camp_prenume, _prenume_invalid
    except ImportError:
        return False
    return _prenume_invalid(_curata_camp_prenume(ov))


def upsert_pacient(cnp: str, nume: str, prenume: Optional[str] = None) -> dict:
    """Insereaza sau actualizeaza pacient. NU suprascrie nume/prenume daca existentul e deja valid."""
    existent = get_pacient_by_cnp(cnp)
    prenume_vechi = (existent or {}).get("prenume") if existent else None
    clear_corrupt_prenume = _sterge_prenume_corupt_la_reupload(prenume, prenume_vechi)

    # Nume tip analiza/etichete - considerate invalide pentru suprascriere
    cond_invalid = (
        "nume = '' OR nume = 'Necunoscut' OR nume LIKE '%Medic%' OR nume LIKE '%Varsta%' "
        "OR nume LIKE '%pacient%' OR nume LIKE '%Data inregistr%' OR nume LIKE '%Data tipar%' "
        "OR LOWER(nume) LIKE '%trimitator%' OR LOWER(nume) LIKE '%medicitrimitator%' "
        "OR LENGTH(nume) > 80 "
        "OR (nume LIKE '% (%)' AND LENGTH(nume) < 35) "
        "OR nume LIKE '''%' "
        "OR (nume LIKE '%, 1%' AND (nume LIKE '%MATEI%' OR nume LIKE '%GHEORGHE%' OR nume LIKE '%ALEXANDRA%')) "
        # OCR: «Prenume: CNP:…» salvat greșit în câmpul nume
        "OR (LOWER(nume) LIKE '%prenume%' AND LOWER(nume) LIKE '%cnp%') "
        # MedLife: proceduri/specialitate lipite de nume (Histeroscopie, OG,)
        "OR LOWER(nume) LIKE '%histeroscop%' OR LOWER(nume) LIKE '%colposcop%' "
        "OR LOWER(nume) LIKE '%laparoscop%' OR LOWER(nume) LIKE '% og,%' "
        "OR LOWER(nume) LIKE '%materno-fetala%' OR LOWER(nume) LIKE '%materno fetala%' "
        "OR LOWER(nume) LIKE '%rejuvenare vaginala%'"
    )
    if _use_sqlite():
        with get_cursor() as cur:
            cur.execute(
                f"""INSERT INTO pacienti (cnp, nume, prenume) VALUES (?, ?, ?)
                ON CONFLICT(cnp) DO UPDATE SET
                  nume = CASE WHEN {cond_invalid}
                         THEN excluded.nume ELSE nume END,
                  prenume = CASE WHEN {cond_invalid}
                         THEN excluded.prenume ELSE prenume END""",
                (cnp, nume, prenume or ""),
            )
            if clear_corrupt_prenume:
                cur.execute("UPDATE pacienti SET prenume = NULL WHERE cnp = ?", (cnp,))
            cur.execute("SELECT id, cnp, nume, prenume, created_at FROM pacienti WHERE cnp = ?", (cnp,))
            return _fetchone_dict(cur) or {}
    # PostgreSQL: % in LIKE trebuie escapat ca %% (psycopg2 interpreteaza % ca placeholder)
    cond_invalid_pg = (
        "pacienti.nume = '' OR pacienti.nume = 'Necunoscut' "
        "OR pacienti.nume LIKE '%%Medic%%' OR pacienti.nume LIKE '%%Varsta%%' "
        "OR pacienti.nume LIKE '%%pacient%%' OR pacienti.nume LIKE '%%Data inregistr%%' "
        "OR pacienti.nume LIKE '%%Data tipar%%' "
        "OR LOWER(pacienti.nume) LIKE '%%trimitator%%' OR LOWER(pacienti.nume) LIKE '%%medicitrimitator%%' "
        "OR LENGTH(pacienti.nume) > 80 "
        "OR (pacienti.nume LIKE '%% (%%' AND LENGTH(pacienti.nume) < 35) "
        "OR pacienti.nume LIKE '''%%' "
        "OR (pacienti.nume LIKE '%%, 1%%' AND (pacienti.nume LIKE '%%MATEI%%' OR pacienti.nume LIKE '%%GHEORGHE%%' OR pacienti.nume LIKE '%%ALEXANDRA%%')) "
        "OR (LOWER(pacienti.nume) LIKE '%%prenume%%' AND LOWER(pacienti.nume) LIKE '%%cnp%%') "
        "OR LOWER(pacienti.nume) LIKE '%%histeroscop%%' OR LOWER(pacienti.nume) LIKE '%%colposcop%%' "
        "OR LOWER(pacienti.nume) LIKE '%%laparoscop%%' OR LOWER(pacienti.nume) LIKE '%% og,%%' "
        "OR LOWER(pacienti.nume) LIKE '%%materno-fetala%%' OR LOWER(pacienti.nume) LIKE '%%materno fetala%%' "
        "OR LOWER(pacienti.nume) LIKE '%%rejuvenare vaginala%%'"
    )
    with get_cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO pacienti (cnp, nume, prenume)
            VALUES (%s, %s, %s)
            ON CONFLICT (cnp) DO UPDATE SET
              nume = CASE WHEN {cond_invalid_pg}
                   THEN EXCLUDED.nume ELSE pacienti.nume END,
              prenume = CASE WHEN {cond_invalid_pg}
                   THEN EXCLUDED.prenume ELSE pacienti.prenume END
            RETURNING id, cnp, nume, prenume, created_at
            """,
            (cnp, nume, prenume or ""),
        )
        row = _fetchone_dict(cur) or {}
        if clear_corrupt_prenume:
            cur.execute("UPDATE pacienti SET prenume = NULL WHERE cnp = %s", (cnp,))
            cur.execute(
                "SELECT id, cnp, nume, prenume, created_at FROM pacienti WHERE cnp = %s",
                (cnp,),
            )
            row = _fetchone_dict(cur) or row
        return row


def update_pacient_nume(cnp: str, nume: str, prenume: Optional[str] = None) -> bool:
    """Actualizeaza numele și prenumele unui pacient. Returneaza True dacă s-a actualizat."""
    with get_cursor() as cur:
        if _use_sqlite():
            cur.execute(
                "UPDATE pacienti SET nume = ?, prenume = ? WHERE cnp = ?",
                (nume.strip(), (prenume or "").strip() or None, cnp),
            )
        else:
            cur.execute(
                "UPDATE pacienti SET nume = %s, prenume = %s WHERE cnp = %s",
                (nume.strip(), (prenume or "").strip() or None, cnp),
            )
        return cur.rowcount > 0


def get_pacient_by_cnp(cnp: str) -> Optional[dict]:
    with get_cursor() as cur:
        if _use_sqlite():
            cur.execute("SELECT id, cnp, nume, prenume, created_at FROM pacienti WHERE cnp = ?", (cnp,))
        else:
            cur.execute("SELECT id, cnp, nume, prenume, created_at FROM pacienti WHERE cnp = %s", (cnp,))
        row = cur.fetchone()
        return _row_to_dict(row) if row else None


# Pacienti cu nume cunoscut de corectat (cnp, nume, prenume)
_PACIENTI_FIX_NUME = [
    ("2470112080077", "VLADASEL", "ELENA"),
    ("1461208080072", "VLADASEL", "AUREL-NICOLAE-SORIN"),
    ("2540207080070", "PETREAN", "ANA"),
    ("1420917080026", "IANCU", "GHEORGHE"),
    ("2970424080038", "MANDACHE", "OANA ALEXANDRA"),
    ("5240222080031", "NITU", "MATEI"),
]


def fix_pacienti_nume_gunoi() -> int:
    """Seteaza 'Necunoscut' pentru pacienti cu nume evident gunoi (Data inregistrari etc.) care nu au corectie cunoscuta."""
    cnps_cunoscuti = {c[0] for c in _PACIENTI_FIX_NUME}
    with get_cursor(commit=False) as cur:
        cur.execute("SELECT id, cnp, nume FROM pacienti WHERE nume != 'Necunoscut' AND nume != ''")
        rows = cur.fetchall()
    n = 0
    for row in rows:
        rid = _row_get(row, "id") or _row_get(row, 0)
        cnp = _row_get(row, "cnp") or _row_get(row, 1)
        nume = _row_get(row, "nume") or _row_get(row, 2)
        if cnp in cnps_cunoscuti:
            continue
        if not _nume_invalid(nume):
            continue
        with get_cursor() as cur:
            ph = "?" if _use_sqlite() else "%s"
            cur.execute(f"UPDATE pacienti SET nume = 'Necunoscut', prenume = NULL WHERE id = {ph}", (rid,))
            n += cur.rowcount
    return n


def fix_pacienti_nume_curatare_completa() -> int:
    """
    Aplica _curata_nume pe TOȚI pacienții - elimină apostrofuri, Varsta:, duplicări etc.
    Rulează la startup pentru a corecta orice nume corupt din OCR/upload-uri anterioare.
    """
    from backend.parser import _curata_nume, _nume_este_gunoi
    cnps_cunoscuti = {c[0] for c in _PACIENTI_FIX_NUME}
    with get_cursor(commit=False) as cur:
        cur.execute("SELECT id, cnp, nume, prenume FROM pacienti")
        rows = cur.fetchall()
    n = 0
    for row in rows:
        rid = _row_get(row, "id") or _row_get(row, 0)
        cnp = (_row_get(row, "cnp") or _row_get(row, 1)) or ""
        nume_raw = _row_get(row, "nume") or _row_get(row, 2) or ""
        prenume_raw = _row_get(row, "prenume") or _row_get(row, 3) or ""
        full_raw = f"{nume_raw} {prenume_raw}".strip()
        full_curat = _curata_nume(full_raw)
        if _nume_este_gunoi(full_curat):
            nume_nou, prenume_nou = "Necunoscut", None
        elif cnp in cnps_cunoscuti:
            nume_nou, prenume_nou = next((c[1], c[2]) for c in _PACIENTI_FIX_NUME if c[0] == cnp)
        elif full_curat and full_curat != "Necunoscut":
            parts = full_curat.split(None, 1)
            nume_nou = parts[0] if parts else "Necunoscut"
            prenume_nou = parts[1] if len(parts) >= 2 else None
        else:
            continue
        if (nume_nou, prenume_nou or "") != (nume_raw, prenume_raw or ""):
            with get_cursor() as cur:
                ph = "?" if _use_sqlite() else "%s"
                cur.execute(
                    f"UPDATE pacienti SET nume = {ph}, prenume = {ph} WHERE id = {ph}",
                    (nume_nou, prenume_nou, rid),
                )
                n += cur.rowcount
    return n


def fix_pacienti_nume_cunoscuti() -> list:
    """Corecteaza numele pacienților cunoscuți cu date corupte (doar cand numele curent e invalid)."""
    rez = []
    for cnp, nume, prenume in _PACIENTI_FIX_NUME:
        pacient = get_pacient_by_cnp(cnp)
        if not pacient or not _nume_invalid(pacient.get("nume")):
            continue  # nu exista sau numele e deja corect
        with get_cursor() as cur:
            if _use_sqlite():
                cur.execute("UPDATE pacienti SET nume = ?, prenume = ? WHERE cnp = ?", (nume, prenume, cnp))
            else:
                cur.execute("UPDATE pacienti SET nume = %s, prenume = %s WHERE cnp = %s", (nume, prenume, cnp))
        rez.append({"cnp": cnp, "nume": nume, "prenume": prenume})
    return rez


# --- Buletine ---
def insert_buletin(pacient_id: int, data_buletin=None, laborator: Optional[str] = None, fisier_original: Optional[str] = None) -> dict:
    with get_cursor() as cur:
        if _use_sqlite():
            cur.execute(
                "INSERT INTO buletine (pacient_id, data_buletin, laborator, fisier_original) VALUES (?, ?, ?, ?)",
                (pacient_id, data_buletin, laborator, fisier_original),
            )
            cur.execute("SELECT id, pacient_id, data_buletin, laborator, fisier_original, created_at FROM buletine ORDER BY id DESC LIMIT 1")
            return _fetchone_dict(cur) or {}
        cur.execute(
            """
            INSERT INTO buletine (pacient_id, data_buletin, laborator, fisier_original)
            VALUES (%s, %s, %s, %s)
            RETURNING id, pacient_id, data_buletin, laborator, fisier_original, created_at
            """,
            (pacient_id, data_buletin, laborator, fisier_original),
        )
        return _fetchone_dict(cur) or {}


# Limite aliniate la schema PostgreSQL (evită crash la INSERT)
_REZ_DEN_MAX = 255
_REZ_UNIT_MAX = 64
_REZ_FLAG_MAX = 16
_REZ_CAT_MAX = 100
# TEXT în PG după migrare 011; plafon rezonabil anti-abuz
_REZ_VALOARE_TEXT_MAX = 500_000
_REZ_META_MAX = 16_384


def rezultat_meta_pentru_insert(
    organism_raw: Optional[str],
    rezultat_tip: Optional[str],
    needs_review: bool = False,
    review_reasons: Optional[List[str]] = None,
    ocr_confidence: Optional[float] = None,
) -> Optional[str]:
    """Construiește JSON pentru coloana rezultat_meta (microbiologie etc.)."""
    import json

    d: Dict[str, str] = {}
    if organism_raw and str(organism_raw).strip():
        clipped = _clip_str(str(organism_raw).strip(), 500)
        if clipped:
            d["organism_raw"] = clipped
    if rezultat_tip and str(rezultat_tip).strip():
        clipped_tip = _clip_str(str(rezultat_tip).strip(), 64)
        if clipped_tip:
            d["rezultat_tip"] = clipped_tip
    if needs_review:
        d["needs_review"] = True
    if review_reasons:
        cleaned_reasons = []
        for reason in review_reasons:
            rr = _clip_str(str(reason), 80)
            if rr:
                cleaned_reasons.append(rr)
        if cleaned_reasons:
            d["review_reasons"] = cleaned_reasons[:20]
    if ocr_confidence is not None:
        try:
            d["ocr_confidence"] = round(float(ocr_confidence), 3)
        except (TypeError, ValueError):
            pass
    if not d:
        return None
    raw_json = json.dumps(d, ensure_ascii=False)
    return _clip_str(raw_json, _REZ_META_MAX)


def _clip_str(s: Optional[str], max_len: int) -> Optional[str]:
    if s is None:
        return None
    t = str(s).strip()
    if not t:
        return None
    return t[:max_len] if len(t) > max_len else t


# --- Rezultate analize ---
def insert_rezultat(buletin_id: int, analiza_standard_id: Optional[int], denumire_raw: Optional[str],
                    valoare=None, valoare_text: Optional[str] = None, unitate: Optional[str] = None,
                    interval_min=None, interval_max=None, flag: Optional[str] = None,
                    ordine: Optional[int] = None, categorie: Optional[str] = None,
                    rezultat_meta: Optional[str] = None) -> dict:
    denumire_raw = _clip_str(denumire_raw, _REZ_DEN_MAX)
    valoare_text = _clip_str(valoare_text, _REZ_VALOARE_TEXT_MAX)
    unitate = _clip_str(unitate, _REZ_UNIT_MAX)
    flag = _clip_str(flag, _REZ_FLAG_MAX)
    categorie = _clip_str(categorie, _REZ_CAT_MAX)
    rezultat_meta = _clip_str(rezultat_meta, _REZ_META_MAX)
    with get_cursor() as cur:
        if _use_sqlite():
            cur.execute(
                """INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie, rezultat_meta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie, rezultat_meta),
            )
            cur.execute("SELECT id, buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie, rezultat_meta, created_at FROM rezultate_analize ORDER BY id DESC LIMIT 1")
            return _fetchone_dict(cur) or {}
        try:
            cur.execute(
                """
                INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie, rezultat_meta)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie, rezultat_meta, created_at
                """,
                (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie, rezultat_meta),
            )
        except Exception as e:
            if "rezultat_meta" in str(e):
                # Coloana nu exista inca — fallback fara rezultat_meta
                cur.connection.rollback()
                cur.execute(
                    """
                    INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie, created_at
                    """,
                    (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie),
                )
            else:
                raise
        return _fetchone_dict(cur) or {}


# --- Căutare analiza_standard_id după alias ---
def get_analiza_standard_id_by_alias(alias: str) -> Optional[int]:
    with get_cursor() as cur:
        if _use_sqlite():
            cur.execute("SELECT analiza_standard_id FROM analiza_alias WHERE LOWER(TRIM(alias)) = LOWER(TRIM(?))", (alias,))
        else:
            cur.execute(
                "SELECT analiza_standard_id FROM analiza_alias WHERE LOWER(TRIM(alias)) = LOWER(TRIM(%s))",
                (alias,),
            )
        row = cur.fetchone()
        if not row:
            return None
        return _row_get(row, 0 if _use_sqlite() else "analiza_standard_id")


# --- Lista si cautare pacienti ---
def count_pacienti(q: Optional[str] = None) -> int:
    """Număr total pacienți. Dacă q e setat, numără doar cei care match-uiesc căutarea."""
    with get_cursor(commit=False) as cur:
        if q and q.strip():
            q_like = f"%{q.strip()}%"
            q_like_lower = f"%{q.strip().lower()}%"
            if _use_sqlite():
                cur.execute(
                    "SELECT COUNT(*) FROM pacienti p "
                    "WHERE p.cnp LIKE ? OR LOWER(COALESCE(p.nume,'') || ' ' || COALESCE(p.prenume,'')) LIKE ?",
                    (q_like, q_like_lower),
                )
            else:
                cur.execute(
                    "SELECT COUNT(*) FROM pacienti p "
                    "WHERE p.cnp LIKE %s OR LOWER(CONCAT(COALESCE(p.nume,''), ' ', COALESCE(p.prenume,''))) LIKE %s",
                    (q_like, q_like_lower),
                )
        else:
            cur.execute("SELECT COUNT(*) FROM pacienti")
        row = cur.fetchone()
        return int(_row_get(row, 0) or 0)


def get_all_pacienti(limit: int = 100, offset: int = 0, q: Optional[str] = None) -> list:
    """Listă pacienți cu paginare. Opțional q pentru căutare după CNP/nume."""
    with get_cursor(commit=False) as cur:
        if q and q.strip():
            q_like = f"%{q.strip()}%"
            q_like_lower = f"%{q.strip().lower()}%"
            if _use_sqlite():
                cur.execute(
                    "SELECT p.id, p.cnp, p.nume, p.prenume, p.created_at, COUNT(b.id) as nr_buletine "
                    "FROM pacienti p LEFT JOIN buletine b ON b.pacient_id = p.id "
                    "WHERE p.cnp LIKE ? OR LOWER(COALESCE(p.nume,'') || ' ' || COALESCE(p.prenume,'')) LIKE ? "
                    "GROUP BY p.id ORDER BY p.nume LIMIT ? OFFSET ?",
                    (q_like, q_like_lower, limit, offset),
                )
            else:
                cur.execute(
                    "SELECT p.id, p.cnp, p.nume, p.prenume, p.created_at, COUNT(b.id) as nr_buletine "
                    "FROM pacienti p LEFT JOIN buletine b ON b.pacient_id = p.id "
                    "WHERE p.cnp LIKE %s OR LOWER(CONCAT(COALESCE(p.nume,''), ' ', COALESCE(p.prenume,''))) LIKE %s "
                    "GROUP BY p.id ORDER BY p.nume LIMIT %s OFFSET %s",
                    (q_like, q_like_lower, limit, offset),
                )
        else:
            if _use_sqlite():
                cur.execute(
                    "SELECT p.id, p.cnp, p.nume, p.prenume, p.created_at, COUNT(b.id) as nr_buletine "
                    "FROM pacienti p LEFT JOIN buletine b ON b.pacient_id = p.id "
                    "GROUP BY p.id ORDER BY p.nume LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            else:
                cur.execute(
                    "SELECT p.id, p.cnp, p.nume, p.prenume, p.created_at, COUNT(b.id) as nr_buletine "
                    "FROM pacienti p LEFT JOIN buletine b ON b.pacient_id = p.id "
                    "GROUP BY p.id ORDER BY p.nume LIMIT %s OFFSET %s",
                    (limit, offset),
                )
        return [_row_to_dict(r) for r in cur.fetchall()]


def get_pacienti_paginat(limit: int = 100, offset: int = 0, q: Optional[str] = None) -> tuple[list, int]:
    """
    Returneaza (items, total) pentru lista pacienti.
    PostgreSQL: un singur query (COUNT OVER) pentru a reduce latenta.
    SQLite/MySQL: fallback la implementarea existenta.
    """
    try:
        limit = max(1, min(int(limit), 500))
    except (TypeError, ValueError):
        limit = 100
    try:
        offset = max(0, int(offset))
    except (TypeError, ValueError):
        offset = 0

    if _use_sqlite() or _detect_db_type() == "mysql":
        items = get_all_pacienti(limit=limit, offset=offset, q=q)
        total = count_pacienti(q=q)
        return items, total

    q_clean = (q or "").strip()
    params: list = []
    where_sql = ""
    if q_clean:
        q_like = f"%{q_clean}%"
        q_like_lower = f"%{q_clean.lower()}%"
        where_sql = (
            "WHERE p.cnp LIKE %s OR "
            "LOWER(CONCAT(COALESCE(p.nume,''), ' ', COALESCE(p.prenume,''))) LIKE %s"
        )
        params.extend([q_like, q_like_lower])

    params.extend([limit, offset])
    with get_cursor(commit=False) as cur:
        cur.execute(
            f"""
            SELECT
                p.id, p.cnp, p.nume, p.prenume, p.created_at,
                COALESCE(bc.nr_buletine, 0)::int AS nr_buletine,
                COUNT(*) OVER()::int AS total_count
            FROM pacienti p
            LEFT JOIN (
                SELECT pacient_id, COUNT(*)::int AS nr_buletine
                FROM buletine
                GROUP BY pacient_id
            ) bc ON bc.pacient_id = p.id
            {where_sql}
            ORDER BY p.nume
            LIMIT %s OFFSET %s
            """,
            tuple(params),
        )
        rows = cur.fetchall()
        if not rows:
            return [], 0
        total = int(_row_get(rows[0], "total_count", 0) or 0)
        items = []
        for r in rows:
            d = _row_to_dict(r) or {}
            d.pop("total_count", None)
            items.append(d)
        return items, total


def search_pacienti(q: str) -> list:
    q_like = f"%{q}%"
    q_like_lower = f"%{q.lower()}%"
    with get_cursor(commit=False) as cur:
        if _use_sqlite():
            cur.execute(
                "SELECT p.id, p.cnp, p.nume, p.prenume, p.created_at, COUNT(b.id) as nr_buletine "
                "FROM pacienti p LEFT JOIN buletine b ON b.pacient_id = p.id "
                "WHERE p.cnp LIKE ? OR LOWER(COALESCE(p.nume,'') || ' ' || COALESCE(p.prenume,'')) LIKE ? "
                "GROUP BY p.id ORDER BY p.nume",
                (q_like, q_like_lower),
            )
        else:
            cur.execute(
                "SELECT p.id, p.cnp, p.nume, p.prenume, p.created_at, COUNT(b.id) as nr_buletine "
                "FROM pacienti p LEFT JOIN buletine b ON b.pacient_id = p.id "
                "WHERE p.cnp LIKE %s OR LOWER(COALESCE(p.nume,'') || ' ' || COALESCE(p.prenume,'')) LIKE %s "
                "GROUP BY p.id ORDER BY p.nume",
                (q_like, q_like_lower),
            )
        return [_row_to_dict(r) for r in cur.fetchall()]


# --- Laboratoare + catalog analize ---
def get_laboratoare() -> list:
    """Lista laboratoare cu numar analize. Returneaza [] daca tabelul nu exista."""
    try:
        with get_cursor(commit=False) as cur:
            if _use_sqlite():
                cur.execute(
                    """SELECT l.id, l.nume, l.website, l.retea,
                              (SELECT COUNT(*) FROM laborator_analize la WHERE la.laborator_id = l.id) as nr_analize
                       FROM laboratoare l ORDER BY l.nume"""
                )
            else:
                cur.execute(
                    """SELECT l.id, l.nume, l.website, l.retea,
                              (SELECT COUNT(*) FROM laborator_analize la WHERE la.laborator_id = l.id)::int as nr_analize
                       FROM laboratoare l ORDER BY l.nume"""
                )
            return [_row_to_dict(r) for r in cur.fetchall()]
    except Exception:
        return []


def get_laborator_analize(laborator_id: int) -> list:
    """Catalog analize pentru un laborator. Returneaza lista cu denumire_standard, cod_standard."""
    try:
        with get_cursor(commit=False) as cur:
            if _use_sqlite():
                cur.execute(
                    """SELECT a.id, a.cod_standard, a.denumire_standard
                       FROM analiza_standard a
                       JOIN laborator_analize la ON la.analiza_standard_id = a.id
                       WHERE la.laborator_id = ?
                       ORDER BY a.denumire_standard""",
                    (laborator_id,),
                )
            else:
                cur.execute(
                    """SELECT a.id, a.cod_standard, a.denumire_standard
                       FROM analiza_standard a
                       JOIN laborator_analize la ON la.analiza_standard_id = a.id
                       WHERE la.laborator_id = %s
                       ORDER BY a.denumire_standard""",
                    (laborator_id,),
                )
            return [_row_to_dict(r) for r in cur.fetchall()]
    except Exception:
        return []


# --- Lista analize standard ---
def get_all_analize_standard() -> list:
    try:
        from backend.analiza_categorii import categorie_grup_pentru_cod
    except Exception:
        # Fallback sigur pentru medii unde fisierul optional nu este in pachetul deploy.
        def categorie_grup_pentru_cod(_cod: str) -> str:
            return ""

    with get_cursor(commit=False) as cur:
        cur.execute("SELECT id, cod_standard, denumire_standard FROM analiza_standard ORDER BY denumire_standard")
        rows = [_row_to_dict(r) for r in cur.fetchall()]
        for r in rows:
            r["categorie_grup"] = categorie_grup_pentru_cod(r.get("cod_standard") or "")
        return rows


def adauga_analiza_standard(denumire: str, cod: str) -> dict:
    """Adauga o noua analiza standard. Returneaza analiza creata sau eroare."""
    cod_norm = cod.upper().strip().replace(" ", "_")
    with get_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = %s", (cod_norm,))
        existing = cur.fetchone()
        if existing:
            raise ValueError(f"Codul '{cod_norm}' exista deja.")
        cur.execute(
            "INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES (%s, %s) RETURNING id, cod_standard, denumire_standard",
            (cod_norm, denumire.strip())
        )
        row = cur.fetchone()
        return _row_to_dict(row)


# --- Istoric pentru un tip de analiza ---
def get_historicul_analiza(analiza_standard_id: int) -> list:
    """Toate rezultatele pentru o analiza standard, grupate pe pacienti."""
    with get_cursor(commit=False) as cur:
        if _use_sqlite():
            cur.execute(
                """SELECT r.id, r.valoare, r.unitate, r.interval_min, r.interval_max, r.flag,
                          r.denumire_raw, b.created_at as data_buletin, b.laborator,
                          p.cnp, p.nume, p.prenume, p.id as pacient_id
                   FROM rezultate_analize r
                   JOIN buletine b ON b.id = r.buletin_id
                   JOIN pacienti p ON p.id = b.pacient_id
                   WHERE r.analiza_standard_id = ?
                   ORDER BY p.nume, b.created_at DESC""",
                (analiza_standard_id,),
            )
        else:
            cur.execute(
                """SELECT r.id, r.valoare, r.unitate, r.interval_min, r.interval_max, r.flag,
                          r.denumire_raw, b.created_at as data_buletin, b.laborator,
                          p.cnp, p.nume, p.prenume, p.id as pacient_id
                   FROM rezultate_analize r
                   JOIN buletine b ON b.id = r.buletin_id
                   JOIN pacienti p ON p.id = b.pacient_id
                   WHERE r.analiza_standard_id = %s
                   ORDER BY p.nume, b.created_at DESC""",
                (analiza_standard_id,),
            )
        return [_row_to_dict(r) for r in cur.fetchall()]


# --- Analize necunoscute (auto-invatare) ---
def get_analize_necunoscute(doar_neaprobate: bool = True) -> list:
    """Returneaza analizele care nu au fost recunoscute de normalizer."""
    with get_cursor(commit=False) as cur:
        if _use_sqlite():
            if doar_neaprobate:
                cur.execute(
                    "SELECT id, denumire_raw, aparitii, aprobata, analiza_standard_id, categorie, created_at, updated_at "
                    "FROM analiza_necunoscuta WHERE aprobata = 0 "
                    "ORDER BY CASE WHEN categorie IS NULL OR categorie = '' THEN 1 ELSE 0 END, categorie, aparitii DESC, denumire_raw"
                )
            else:
                cur.execute(
                    "SELECT id, denumire_raw, aparitii, aprobata, analiza_standard_id, categorie, created_at, updated_at "
                    "FROM analiza_necunoscuta ORDER BY aprobata, aparitii DESC"
                )
        else:
            ord_by = (
                " ORDER BY CASE WHEN categorie IS NULL OR categorie = '' THEN 1 ELSE 0 END, "
                "categorie, aparitii DESC, denumire_raw"
            )
            q = "SELECT * FROM analiza_necunoscuta" + (" WHERE aprobata=0" if doar_neaprobate else "") + ord_by
            try:
                cur.execute(q)
            except Exception:
                # PostgreSQL fără migrare 012 (coloana categorie) — tranzacția e invalidă până la rollback
                try:
                    cur.connection.rollback()
                except Exception:
                    pass
                ord_simple = " ORDER BY aparitii DESC, denumire_raw"
                q2 = "SELECT * FROM analiza_necunoscuta" + (" WHERE aprobata=0" if doar_neaprobate else "") + ord_simple
                cur.execute(q2)
        return [_row_to_dict(r) for r in cur.fetchall()]


def get_necunoscute_by_ids(ids: list) -> list:
    """
    Rânduri din analiza_necunoscuta (doar neaprobate) după id-uri.
    Folosit pentru aprobare în masă și pentru lookup denumire_raw fără a o pune în URL/JS.
    """
    clean: list[int] = []
    for x in ids or []:
        try:
            clean.append(int(x))
        except (TypeError, ValueError):
            continue
    if not clean:
        return []
    with get_cursor(commit=False) as cur:
        if _use_sqlite():
            ph = ",".join("?" * len(clean))
            cur.execute(
                f"SELECT id, denumire_raw FROM analiza_necunoscuta "
                f"WHERE aprobata = 0 AND id IN ({ph})",
                clean,
            )
        else:
            ph = ",".join(["%s"] * len(clean))
            cur.execute(
                f"SELECT id, denumire_raw FROM analiza_necunoscuta "
                f"WHERE aprobata = 0 AND id IN ({ph})",
                tuple(clean),
            )
        return [_row_to_dict(r) for r in cur.fetchall()]


def backfill_categorie_necunoscuta_din_rezultate(
    dry_run: bool = True,
    limit: Optional[int] = None,
) -> dict:
    """
    Completează analiza_necunoscuta.categorie din rezultate_analize: pentru fiecare
    denumire_raw fără categorie la necunoscute, folosește cel mai recent rând din
    rezultate (ORDER BY id DESC) care are categorie setată (secțiunea din buletin).

    :param dry_run: dacă True, nu scrie în DB, doar numără și returnează eșantion.
    :param limit: opțional, max. rânduri din analiza_necunoscuta de examinat.
    """
    ph = "?" if _use_sqlite() else "%s"
    stats: dict = {
        "dry_run": dry_run,
        "examinat": 0,
        "cu_categorie_gasita": 0,
        "fara_categorie_in_rezultate": 0,
        "actualizate": 0,
        "esantion": [],
    }
    where_empty = "(categorie IS NULL OR TRIM(categorie) = '')"
    sql_nec = f"SELECT id, denumire_raw FROM analiza_necunoscuta WHERE {where_empty}"
    if limit is not None and limit > 0:
        lim = int(limit)
        if _use_sqlite():
            sql_nec += f" LIMIT {lim}"
        else:
            sql_nec += f" LIMIT {lim}"

    sql_cat = (
        f"SELECT categorie FROM rezultate_analize WHERE denumire_raw = {ph} "
        f"AND categorie IS NOT NULL AND TRIM(categorie) != '' ORDER BY id DESC LIMIT 1"
    )

    with get_cursor(commit=not dry_run) as cur:
        cur.execute(sql_nec)
        nec_rows = [
            nr for nr in (_row_to_dict(r) for r in cur.fetchall() if r is not None) if nr
        ]

        for nr in nec_rows:
            stats["examinat"] += 1
            rid = nr.get("id")
            raw = (nr.get("denumire_raw") or "").strip()
            if rid is None or not raw:
                stats["fara_categorie_in_rezultate"] += 1
                continue

            cur.execute(sql_cat, (raw,))
            cd = _fetchone_dict(cur)
            cat = (cd or {}).get("categorie") if cd else None
            if cat is None:
                stats["fara_categorie_in_rezultate"] += 1
                continue
            cat = str(cat).strip()
            if not cat:
                stats["fara_categorie_in_rezultate"] += 1
                continue

            stats["cu_categorie_gasita"] += 1
            if len(stats["esantion"]) < 30:
                stats["esantion"].append(
                    {"id": rid, "denumire_raw": raw[:80], "categorie": cat[:100]}
                )

            if not dry_run:
                cur.execute(
                    f"UPDATE analiza_necunoscuta SET categorie = {ph} WHERE id = {ph}",
                    (cat, rid),
                )
                stats["actualizate"] += 1

    if dry_run:
        stats["actualizate"] = stats["cu_categorie_gasita"]

    return stats


def curata_gunoi_analize_pipeline(
    dry_run: bool = True,
    sterge_rezultate_nemapate: bool = False,
    doar_neaprobate_necunoscute: bool = True,
) -> dict:
    """
    Șterge intrări gunoi folosind aceleași reguli ca ``backend.parser.este_denumire_gunoi``
    (sincron cu normalizer-ul, care nu mai loghează gunoi).

    - analiza_necunoscuta: implicit doar rânduri cu aprobata=0 (listă „de asociat”).
    - rezultate_analize: opțional, rânduri cu analiza_standard_id IS NULL și denumire gunoi.

    :param dry_run: nu execută DELETE dacă True.
    :param sterge_rezultate_nemapate: curăță și rezultatele din buletine (fără mapare).
    :param doar_neaprobate_necunoscute: dacă False, include și rânduri aprobate (rar; folosiți cu grijă).
    """
    from backend.parser import este_denumire_gunoi

    ph = "?" if _use_sqlite() else "%s"
    stats: dict = {
        "dry_run": dry_run,
        "necunoscute_scanate": 0,
        "necunoscute_sterse": 0,
        "rezultate_scanate": 0,
        "rezultate_sterse": 0,
        "exemple_necunoscute": [],
        "exemple_rezultate": [],
    }

    sql_nec = "SELECT id, denumire_raw FROM analiza_necunoscuta"
    if doar_neaprobate_necunoscute:
        sql_nec += " WHERE aprobata = 0"

    with get_cursor(commit=not dry_run) as cur:
        cur.execute(sql_nec)
        for row in cur.fetchall():
            d = _row_to_dict(row)
            stats["necunoscute_scanate"] += 1
            raw = d.get("denumire_raw") or ""
            if not este_denumire_gunoi(raw):
                continue
            stats["necunoscute_sterse"] += 1
            if len(stats["exemple_necunoscute"]) < 30:
                stats["exemple_necunoscute"].append(
                    {"id": d.get("id"), "denumire_raw": (raw or "")[:120]}
                )
            if not dry_run:
                cur.execute(f"DELETE FROM analiza_necunoscuta WHERE id = {ph}", (d["id"],))

        if sterge_rezultate_nemapate:
            cur.execute(
                "SELECT id, denumire_raw FROM rezultate_analize WHERE analiza_standard_id IS NULL"
            )
            for row in cur.fetchall():
                d = _row_to_dict(row)
                stats["rezultate_scanate"] += 1
                raw = d.get("denumire_raw") or ""
                if not este_denumire_gunoi(raw):
                    continue
                stats["rezultate_sterse"] += 1
                if len(stats["exemple_rezultate"]) < 30:
                    stats["exemple_rezultate"].append(
                        {"id": d.get("id"), "denumire_raw": (raw or "")[:120]}
                    )
                if not dry_run:
                    cur.execute(f"DELETE FROM rezultate_analize WHERE id = {ph}", (d["id"],))

    return stats


def sterge_analiza_necunoscuta(id_necunoscuta: int) -> bool:
    """Sterge o intrare din analiza_necunoscuta (ex: dupa ce a fost aprobata sau ignorata)."""
    with get_cursor() as cur:
        if _use_sqlite():
            cur.execute("DELETE FROM analiza_necunoscuta WHERE id = ?", (id_necunoscuta,))
        else:
            cur.execute("DELETE FROM analiza_necunoscuta WHERE id = %s", (id_necunoscuta,))
    return True


def goleste_analize_asociate() -> dict:
    """Șterge toate intrările din analiza_necunoscuta și analiza_alias (asocierile din secțiunea Asociază cu analiza standard)."""
    with get_cursor() as cur:
        if _use_sqlite():
            cur.execute("DELETE FROM analiza_necunoscuta")
            cur.execute("DELETE FROM analiza_alias")
        else:
            cur.execute("DELETE FROM analiza_necunoscuta")
            cur.execute("DELETE FROM analiza_alias")
    return {"ok": True, "mesaj": "Toate asocierile au fost șterse."}


def get_historicul_analiza_by_cod(cod_standard: str) -> list:
    with get_cursor(commit=False) as cur:
        if _use_sqlite():
            cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = ?", (cod_standard,))
        else:
            cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = %s", (cod_standard,))
        row = cur.fetchone()
        if not row:
            return []
        aid = _row_get(row, 0 if _use_sqlite() else "id")
    return get_historicul_analiza(aid)


# --- GET /pacient/{cnp} ---
def get_pacient_cu_analize(cnp: str) -> Optional[dict]:
    """Pacient cu buletine si rezultate. Optimizat: 2 query-uri in loc de N+1."""
    pacient = get_pacient_by_cnp(cnp)
    if not pacient:
        return None
    with get_cursor(commit=False) as cur:
        if _use_sqlite():
            cur.execute(
                "SELECT id, pacient_id, data_buletin, laborator, fisier_original, created_at FROM buletine WHERE pacient_id = ? ORDER BY created_at DESC",
                (pacient["id"],),
            )
        else:
            cur.execute(
                "SELECT id, pacient_id, data_buletin, laborator, fisier_original, created_at FROM buletine WHERE pacient_id = %s ORDER BY created_at DESC",
                (pacient["id"],),
            )
        buletine = [_row_to_dict(r) for r in cur.fetchall()]
    if not buletine:
        pacient["buletine"] = []
        return pacient
    ids_buletin = [b["id"] for b in buletine]
    placeholders = ",".join(["?" if _use_sqlite() else "%s"] * len(ids_buletin))
    with get_cursor(commit=False) as cur:
        if _use_sqlite():
            cur.execute(
                """SELECT r.id, r.buletin_id, r.analiza_standard_id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate, r.interval_min, r.interval_max, r.flag, r.ordine, r.categorie, r.created_at, a.cod_standard, a.denumire_standard
                FROM rezultate_analize r LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id WHERE r.buletin_id IN (""" + placeholders + """) ORDER BY r.buletin_id, COALESCE(r.ordine, 99999), a.denumire_standard, r.denumire_raw""",
                ids_buletin,
            )
        else:
            cur.execute(
                """SELECT r.id, r.buletin_id, r.analiza_standard_id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate, r.interval_min, r.interval_max, r.flag, r.ordine, r.categorie, r.created_at, a.cod_standard, a.denumire_standard
                FROM rezultate_analize r LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id WHERE r.buletin_id IN (""" + placeholders + """) ORDER BY r.buletin_id, COALESCE(r.ordine, 99999), a.denumire_standard NULLS LAST, r.denumire_raw""",
                ids_buletin,
            )
        toate_rez = [_row_to_dict(r) for r in cur.fetchall()]
    by_buletin = {}
    for r in toate_rez:
        bid = r.get("buletin_id")
        if bid not in by_buletin:
            by_buletin[bid] = []
        by_buletin[bid].append(r)
    for b in buletine:
        b["rezultate"] = by_buletin.get(b["id"], [])
    pacient["buletine"] = buletine
    return pacient


# --- Users (autentificare) ---
_USERS_INIT_DONE = False


def _init_users_table():
    """Creeaza tabelul users daca nu exista (SQLite + PostgreSQL)."""
    global _USERS_INIT_DONE
    if _USERS_INIT_DONE:
        return
    with get_cursor() as cur:
        if _use_sqlite():
            sql_dir = Path(__file__).resolve().parent.parent / "sql"
            path = sql_dir / "003_users_auth.sql"
            if path.exists():
                cur.connection.executescript(path.read_text(encoding="utf-8"))
        else:
            # PostgreSQL / MySQL
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                cur.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            except Exception:
                pass
    _USERS_INIT_DONE = True


def get_user_by_username(username: str) -> Optional[dict]:
    """Returneaza user-ul dupa username sau None."""
    _init_users_table()
    with get_cursor(commit=False) as cur:
        if _use_sqlite():
            cur.execute("SELECT id, username, password_hash FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),))
        else:
            cur.execute("SELECT id, username, password_hash FROM users WHERE LOWER(username) = LOWER(%s)", (username.strip(),))
        row = cur.fetchone()
        return _row_to_dict(row) if row else None


def create_user(username: str, password_hash: str) -> Optional[dict]:
    """Creeaza un utilizator nou. Returneaza None daca username exista deja."""
    _init_users_table()
    try:
        with get_cursor() as cur:
            if _use_sqlite():
                cur.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username.strip(), password_hash),
                )
                cur.execute("SELECT id, username, created_at FROM users WHERE id = last_insert_rowid()")
                row = cur.fetchone()
            else:
                cur.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id, username, created_at",
                    (username.strip(), password_hash),
                )
                row = cur.fetchone()
            return _row_to_dict(row) if row else {"id": None, "username": username.strip()}
    except Exception:
        return None


def ensure_default_admin() -> bool:
    """Creeaza utilizatorul 'admin' cu parola 'admin123' daca nu exista niciun user."""
    _init_users_table()
    with get_cursor(commit=False) as cur:
        cur.execute("SELECT COUNT(*) FROM users")
        row = cur.fetchone()
        if not row:
            cnt = 0
        elif hasattr(row, "keys"):
            cnt = list(row.values())[0] if row else 0
        else:
            cnt = _row_get(row, 0, 0)
        if cnt > 0:
            return False
    from backend.auth import hash_password
    create_user("admin", hash_password("admin123"))
    return True


def get_all_users() -> list:
    """Lista toti utilizatorii (fara password_hash)."""
    _init_users_table()
    with get_cursor(commit=False) as cur:
        if _use_sqlite():
            cur.execute("SELECT id, username, created_at FROM users ORDER BY username")
        else:
            cur.execute("SELECT id, username, created_at FROM users ORDER BY username")
        return [_row_to_dict(r) for r in cur.fetchall()]


def update_user_password(username: str, new_password_hash: str) -> bool:
    """Actualizeaza parola unui utilizator."""
    _init_users_table()
    try:
        with get_cursor() as cur:
            if _use_sqlite():
                cur.execute("UPDATE users SET password_hash = ? WHERE LOWER(username) = LOWER(?)", (new_password_hash, username.strip()))
            else:
                cur.execute("UPDATE users SET password_hash = %s WHERE LOWER(username) = LOWER(%s)", (new_password_hash, username.strip()))
            return cur.rowcount > 0
    except Exception:
        return False


def delete_user_by_id(user_id: int) -> bool:
    """Sterge un utilizator dupa id. Returneaza True daca s-a sters."""
    _init_users_table()
    try:
        with get_cursor() as cur:
            if _use_sqlite():
                cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
            else:
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            return cur.rowcount > 0
    except Exception:
        return False


def delete_buletin(buletin_id: int) -> bool:
    """Sterge un buletin si toate analizele lui. Returneaza True daca s-a sters."""
    try:
        with get_cursor() as cur:
            if _use_sqlite():
                cur.execute("DELETE FROM rezultate_analize WHERE buletin_id = ?", (buletin_id,))
                cur.execute("DELETE FROM buletine WHERE id = ?", (buletin_id,))
            else:
                cur.execute("DELETE FROM rezultate_analize WHERE buletin_id = %s", (buletin_id,))
                cur.execute("DELETE FROM buletine WHERE id = %s", (buletin_id,))
            return cur.rowcount > 0
    except Exception:
        return False


def delete_pacient(pacient_id: int) -> bool:
    """Sterge un pacient cu toate buletinele si analizele lui."""
    try:
        with get_cursor() as cur:
            if _use_sqlite():
                cur.execute(
                    "DELETE FROM rezultate_analize WHERE buletin_id IN (SELECT id FROM buletine WHERE pacient_id = ?)",
                    (pacient_id,),
                )
                cur.execute("DELETE FROM buletine WHERE pacient_id = ?", (pacient_id,))
                cur.execute("DELETE FROM pacienti WHERE id = ?", (pacient_id,))
            else:
                cur.execute(
                    "DELETE FROM rezultate_analize WHERE buletin_id IN (SELECT id FROM buletine WHERE pacient_id = %s)",
                    (pacient_id,),
                )
                cur.execute("DELETE FROM buletine WHERE pacient_id = %s", (pacient_id,))
                cur.execute("DELETE FROM pacienti WHERE id = %s", (pacient_id,))
            return cur.rowcount > 0
    except Exception as e:
        import logging
        logging.error(f"delete_pacient({pacient_id}) error: {e}")
        return False


# --- Editare manuala rezultate ---

def get_rezultate_buletin(buletin_id: int) -> list:
    """Returneaza toate rezultatele unui buletin, cu denumire_standard si flag."""
    ph = "?" if _use_sqlite() else "%s"
    sql_cu_meta = f"""
                SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate, r.flag,
                       r.interval_min, r.interval_max,
                       r.analiza_standard_id, r.ordine, r.categorie, r.rezultat_meta,
                       a.denumire_standard, a.cod_standard
                FROM rezultate_analize r
                LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
                WHERE r.buletin_id = {ph}
                ORDER BY COALESCE(r.ordine, 99999), a.denumire_standard NULLS LAST, r.denumire_raw
            """
    sql_fara_meta = f"""
                SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate, r.flag,
                       r.interval_min, r.interval_max,
                       r.analiza_standard_id, r.ordine, r.categorie,
                       a.denumire_standard, a.cod_standard
                FROM rezultate_analize r
                LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
                WHERE r.buletin_id = {ph}
                ORDER BY COALESCE(r.ordine, 99999), a.denumire_standard NULLS LAST, r.denumire_raw
            """
    try:
        with get_cursor(commit=False) as cur:
            try:
                cur.execute(sql_cu_meta, (buletin_id,))
            except Exception:
                cur.execute(sql_fara_meta, (buletin_id,))
            rows = cur.fetchall()
            return [_row_to_dict(r) for r in rows] if rows else []
    except Exception:
        return []


def update_rezultat(rezultat_id: int, body: dict) -> bool:
    """Actualizeaza partial un rezultat existent (editare manuala).
    Actualizeaza DOAR campurile prezente in body, fara sa stearga celelalte.
    """
    CAMPURI_PERMISE = {'valoare', 'unitate', 'flag', 'analiza_standard_id'}
    updates = {k: v for k, v in body.items() if k in CAMPURI_PERMISE}
    if not updates:
        return True  # nimic de actualizat
    try:
        with get_cursor() as cur:
            ph = "?" if _use_sqlite() else "%s"
            set_clauses = ", ".join(f"{k} = {ph}" for k in updates)
            values = list(updates.values()) + [rezultat_id]
            cur.execute(
                f"UPDATE rezultate_analize SET {set_clauses} WHERE id = {ph}",
                values,
            )
            return cur.rowcount > 0
    except Exception as e:
        import logging
        logging.error(f"update_rezultat error: {e}")
        return False


def delete_rezultat_single(rezultat_id: int) -> bool:
    """Sterge un singur rezultat dintr-un buletin."""
    try:
        with get_cursor() as cur:
            ph = "?" if _use_sqlite() else "%s"
            cur.execute(f"DELETE FROM rezultate_analize WHERE id={ph}", (rezultat_id,))
            return cur.rowcount > 0
    except Exception:
        return False


def add_rezultat_manual(buletin_id: int, analiza_standard_id: Optional[int],
                        denumire_raw: str, valoare: float, unitate: Optional[str],
                        flag: Optional[str]) -> Optional[dict]:
    """Adauga manual un rezultat intr-un buletin existent."""
    try:
        dn = _clip_str(denumire_raw, _REZ_DEN_MAX) or ""
        un = _clip_str(unitate, _REZ_UNIT_MAX)
        fl = _clip_str(flag, _REZ_FLAG_MAX)
        with get_cursor() as cur:
            ph = "?" if _use_sqlite() else "%s"
            cur.execute(f"""
                INSERT INTO rezultate_analize
                    (buletin_id, analiza_standard_id, denumire_raw, valoare, unitate, flag)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph})
                RETURNING id
            """, (buletin_id, analiza_standard_id, dn, valoare, un, fl))
            row = cur.fetchone()
            if row is None:
                return None
            row_id = _row_get(row, "id" if hasattr(row, "keys") else 0)
            return {"id": row_id}
    except Exception as e:
        import logging
        logging.error(f"add_rezultat_manual error: {e}")
        return None


# --- Export backup (JSON) ---
def _json_serializable(val: Any) -> Any:
    """Convertește o valoare la forma serializabilă JSON (datetime, Decimal, etc.)."""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, dict):
        return {k: _json_serializable(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_json_serializable(v) for v in val]
    return val


def export_backup_data() -> Dict[str, Any]:
    """
    Exportă toate datele de aplicație (fără users) pentru backup.
    Returnează un dict cu: exported_at, schema_version, pacienti, analiza_standard,
    analiza_alias, buletine, rezultate_analize. Toate valorile sunt JSON-serializabile.
    """
    now = datetime.utcnow()
    out: Dict[str, Any] = {
        "exported_at": now.isoformat() + "Z",
        "schema_version": 1,
        "pacienti": [],
        "analiza_standard": [],
        "analiza_alias": [],
        "buletine": [],
        "rezultate_analize": [],
    }
    with get_cursor(commit=False) as cur:
        cur.execute("SELECT id, cnp, nume, prenume, created_at FROM pacienti ORDER BY id")
        out["pacienti"] = [_json_serializable(_row_to_dict(r)) for r in cur.fetchall()]
        cur.execute("SELECT id, cod_standard, denumire_standard FROM analiza_standard ORDER BY id")
        out["analiza_standard"] = [_json_serializable(_row_to_dict(r)) for r in cur.fetchall()]
        cur.execute("SELECT id, analiza_standard_id, alias FROM analiza_alias ORDER BY id")
        out["analiza_alias"] = [_json_serializable(_row_to_dict(r)) for r in cur.fetchall()]
        cur.execute(
            "SELECT id, pacient_id, data_buletin, laborator, fisier_original, created_at FROM buletine ORDER BY id"
        )
        out["buletine"] = [_json_serializable(_row_to_dict(r)) for r in cur.fetchall()]
        # Rezultate: încearcă cu ordine/categorie/rezultat_meta; fallback schema veche
        try:
            cur.execute(
                """SELECT id, buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text,
                          unitate, interval_min, interval_max, flag, ordine, categorie, rezultat_meta, created_at
                   FROM rezultate_analize ORDER BY id"""
            )
        except Exception:
            try:
                cur.execute(
                    """SELECT id, buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text,
                              unitate, interval_min, interval_max, flag, ordine, categorie, created_at
                       FROM rezultate_analize ORDER BY id"""
                )
            except Exception:
                cur.execute(
                    """SELECT id, buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text,
                              unitate, interval_min, interval_max, flag, created_at
                       FROM rezultate_analize ORDER BY id"""
                )
        out["rezultate_analize"] = [_json_serializable(_row_to_dict(r)) for r in cur.fetchall()]
    return out


def _get_or_create_analiza_standard(cod: str, denumire: str) -> int:
    """Returneaza id-ul analizei standard (existenta sau nou creata)."""
    cod_norm = (cod or "").upper().strip().replace(" ", "_")
    if not cod_norm:
        raise ValueError("Cod analiza nu poate fi gol")
    with get_cursor(commit=True) as cur:
        ph = "?" if _use_sqlite() else "%s"
        cur.execute(f"SELECT id FROM analiza_standard WHERE cod_standard = {ph}", (cod_norm,))
        row = cur.fetchone()
        if row:
            return _row_get(row, 0 if _use_sqlite() else "id")
        cur.execute(
            f"INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES ({ph}, {ph})",
            (cod_norm, (denumire or cod_norm).strip()),
        )
        if _use_sqlite():
            rid = cur.lastrowid
            if rid:
                return rid
        cur.execute(f"SELECT id FROM analiza_standard WHERE cod_standard = {ph}", (cod_norm,))
        row = cur.fetchone()
        return _row_get(row, 0 if _use_sqlite() else "id", 0) or 0


def _insert_alias_if_not_exists(analiza_standard_id: int, alias: str) -> None:
    """Insereaza alias daca nu exista (ignora duplicate)."""
    if not alias or not alias.strip():
        return
    with get_cursor(commit=True) as cur:
        if _use_sqlite():
            cur.execute(
                "INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) VALUES (?, ?)",
                (analiza_standard_id, alias.strip()),
            )
        else:
            cur.execute(
                """INSERT INTO analiza_alias (analiza_standard_id, alias) VALUES (%s, %s)
                   ON CONFLICT (alias) DO NOTHING""",
                (analiza_standard_id, alias.strip()),
            )


def restore_from_backup(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Restaureaza date din backup JSON. Adauga peste datele existente (nu sterge).
    Returneaza: {pacienti: n, analiza_standard: n, analiza_alias: n, buletine: n, rezultate: n, erori: []}
    """
    result = {"pacienti": 0, "analiza_standard": 0, "analiza_alias": 0, "buletine": 0, "rezultate": 0, "erori": []}
    if not isinstance(data, dict):
        result["erori"].append("Format invalid: nu este JSON valid")
        return result

    analize_map = {}  # old_id -> new_id
    pacienti_map = {}  # old_id -> new_id
    buletine_map = {}  # old_id -> new_id

    # 1. analiza_standard
    for a in data.get("analiza_standard") or []:
        try:
            cod = a.get("cod_standard")
            denumire = a.get("denumire_standard", "")
            if not cod:
                continue
            old_id = a.get("id")
            new_id = _get_or_create_analiza_standard(cod, denumire)
            if old_id is not None:
                analize_map[old_id] = new_id
            result["analiza_standard"] += 1
        except Exception as e:
            result["erori"].append(f"analiza_standard {a.get('cod_standard')}: {e}")

    # 2. analiza_alias
    for al in data.get("analiza_alias") or []:
        try:
            old_aid = al.get("analiza_standard_id")
            new_aid = analize_map.get(old_aid) if old_aid is not None else None
            if new_aid is None:
                continue
            _insert_alias_if_not_exists(new_aid, al.get("alias") or "")
            result["analiza_alias"] += 1
        except Exception as e:
            result["erori"].append(f"analiza_alias: {e}")

    # 3. pacienti
    for p in data.get("pacienti") or []:
        try:
            cnp = (p.get("cnp") or "").strip()
            if not cnp:
                continue
            upsert_pacient(cnp, p.get("nume") or "", p.get("prenume") or None)
            new_p = get_pacient_by_cnp(cnp)
            if new_p:
                old_id = p.get("id")
                if old_id is not None:
                    pacienti_map[old_id] = new_p["id"]
                result["pacienti"] += 1
        except Exception as e:
            result["erori"].append(f"pacient {p.get('cnp')}: {e}")

    # 4. buletine
    for b in data.get("buletine") or []:
        try:
            old_pid = b.get("pacient_id")
            new_pid = pacienti_map.get(old_pid) if old_pid is not None else None
            if new_pid is None:
                continue
            data_b = b.get("data_buletin")
            laborator = b.get("laborator")
            fisier = b.get("fisier_original")
            new_b = insert_buletin(new_pid, data_b, laborator, fisier)
            old_bid = b.get("id")
            if old_bid is not None and new_b:
                buletine_map[old_bid] = new_b["id"]
            result["buletine"] += 1
        except Exception as e:
            result["erori"].append(f"buletin pacient_id={b.get('pacient_id')}: {e}")

    # 5. rezultate_analize
    for r in data.get("rezultate_analize") or []:
        try:
            old_bid = r.get("buletin_id")
            new_bid = buletine_map.get(old_bid) if old_bid is not None else None
            if new_bid is None:
                continue
            old_aid = r.get("analiza_standard_id")
            new_aid = analize_map.get(old_aid) if old_aid is not None else None
            insert_rezultat(
                new_bid,
                new_aid,
                r.get("denumire_raw"),
                r.get("valoare"),
                r.get("valoare_text"),
                r.get("unitate"),
                r.get("interval_min"),
                r.get("interval_max"),
                r.get("flag"),
                r.get("ordine"),
                r.get("categorie"),
                r.get("rezultat_meta"),
            )
            result["rezultate"] += 1
        except Exception as e:
            result["erori"].append(f"rezultat buletin_id={r.get('buletin_id')}: {e}")

    return result


# --- Upload async jobs (PostgreSQL: partajat intre replici Railway) ---
_UPLOAD_ASYNC_JOBS_TABLE_OK = False


def upload_async_jobs_use_database() -> bool:
    return _detect_db_type() == "postgresql"


def ensure_upload_async_jobs_table() -> None:
    global _UPLOAD_ASYNC_JOBS_TABLE_OK
    if _UPLOAD_ASYNC_JOBS_TABLE_OK or not upload_async_jobs_use_database():
        _UPLOAD_ASYNC_JOBS_TABLE_OK = True
        return
    sql_path = Path(__file__).resolve().parent.parent / "sql" / "017_pg_upload_async_jobs.sql"
    sql_text = sql_path.read_text(encoding="utf-8") if sql_path.exists() else ""
    if not sql_text.strip():
        sql_text = """
        CREATE TABLE IF NOT EXISTS upload_async_jobs (
          job_id VARCHAR(80) PRIMARY KEY,
          owner_username TEXT NOT NULL DEFAULT '',
          file_name TEXT,
          status VARCHAR(32) NOT NULL DEFAULT 'queued',
          created_at TEXT,
          started_at TEXT,
          finished_at TEXT,
          created_ts DOUBLE PRECISION DEFAULT 0,
          started_ts DOUBLE PRECISION DEFAULT 0,
          finished_ts DOUBLE PRECISION DEFAULT 0,
          response_status INTEGER,
          result_json TEXT
        );
        """
    with get_cursor() as cur:
        cur.execute(sql_text)
    _UPLOAD_ASYNC_JOBS_TABLE_OK = True


def _upload_job_row_to_dict(row: dict) -> dict:
    if not row:
        return {}
    d = dict(row)
    rj = d.pop("result_json", None)
    own = d.pop("owner_username", "") or ""
    out: Dict[str, Any] = {**d, "owner": own}
    if rj:
        try:
            out["result"] = json.loads(rj)
        except Exception:
            out["result"] = None
    return out


def upload_async_job_merge_db(job_id: str, **fields: Any) -> dict:
    ensure_upload_async_jobs_table()
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT job_id, owner_username, file_name, status, created_at, started_at, finished_at,
                   created_ts, started_ts, finished_ts, response_status, result_json
            FROM upload_async_jobs WHERE job_id = %s
            """,
            (job_id,),
        )
        row = cur.fetchone()
        base = _upload_job_row_to_dict(row) if row else {"job_id": job_id}
        base.update(fields)
        rj = None
        if base.get("result") is not None:
            rj = json.dumps(base["result"], ensure_ascii=False)
        owner = base.get("owner") or ""
        cur.execute(
            """
            INSERT INTO upload_async_jobs (
              job_id, owner_username, file_name, status, created_at, started_at, finished_at,
              created_ts, started_ts, finished_ts, response_status, result_json
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (job_id) DO UPDATE SET
              owner_username = EXCLUDED.owner_username,
              file_name = EXCLUDED.file_name,
              status = EXCLUDED.status,
              created_at = EXCLUDED.created_at,
              started_at = EXCLUDED.started_at,
              finished_at = EXCLUDED.finished_at,
              created_ts = EXCLUDED.created_ts,
              started_ts = EXCLUDED.started_ts,
              finished_ts = EXCLUDED.finished_ts,
              response_status = EXCLUDED.response_status,
              result_json = EXCLUDED.result_json
            """,
            (
                job_id,
                owner,
                base.get("file_name"),
                base.get("status") or "queued",
                base.get("created_at"),
                base.get("started_at"),
                base.get("finished_at"),
                float(base.get("created_ts") or 0),
                float(base.get("started_ts") or 0),
                float(base.get("finished_ts") or 0),
                base.get("response_status"),
                rj,
            ),
        )
    return base


def upload_async_job_get_db(job_id: str) -> Optional[dict]:
    ensure_upload_async_jobs_table()
    with get_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT job_id, owner_username, file_name, status, created_at, started_at, finished_at,
                   created_ts, started_ts, finished_ts, response_status, result_json
            FROM upload_async_jobs WHERE job_id = %s
            """,
            (job_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return _upload_job_row_to_dict(row)


def upload_async_jobs_prune_db(ttl_seconds: int, max_jobs: int) -> None:
    ensure_upload_async_jobs_table()
    now = time.time()
    with get_cursor() as cur:
        cur.execute(
            """
            DELETE FROM upload_async_jobs
            WHERE finished_ts IS NOT NULL AND finished_ts > 0 AND %s - finished_ts > %s
            """,
            (now, float(ttl_seconds)),
        )
        cur.execute("SELECT COUNT(*) AS n FROM upload_async_jobs")
        row = cur.fetchone()
        n = int(_row_get(row, "n") if row else 0)
        if n > max_jobs:
            excess = n - max_jobs
            cur.execute(
                """
                DELETE FROM upload_async_jobs
                WHERE job_id IN (
                  SELECT job_id FROM upload_async_jobs
                  ORDER BY created_ts ASC NULLS LAST
                  LIMIT %s
                )
                """,
                (excess,),
            )
