"""Conexiune SQLite (implicit), PostgreSQL sau MySQL. CRUD pentru MVP."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from config import settings

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
        for fname in ["schema_sqlite.sql", "seed_sqlite.sql", "002_analize_extinse.sql"]:
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


def _row_to_dict(row) -> dict:
    if row is None:
        return None
    if hasattr(row, "keys"):
        return dict(row)
    return dict(zip([c[0] for c in row.description], row))


# --- Pacienti ---
# NU suprascrie nume/prenume daca existentul e deja valid (evita corupere la upload repetat)
def upsert_pacient(cnp: str, nume: str, prenume: Optional[str] = None) -> dict:
    if _use_sqlite():
        with get_cursor() as cur:
            cur.execute(
                """INSERT INTO pacienti (cnp, nume, prenume) VALUES (?, ?, ?)
                ON CONFLICT(cnp) DO UPDATE SET
                  nume = CASE WHEN nume = '' OR nume = 'Necunoscut' OR nume LIKE '%Medic%' OR nume LIKE '%Varsta%' OR nume LIKE '%pacient%' OR LENGTH(nume) > 80
                         THEN excluded.nume ELSE nume END,
                  prenume = CASE WHEN nume = '' OR nume = 'Necunoscut' OR nume LIKE '%Medic%' OR nume LIKE '%Varsta%' OR nume LIKE '%pacient%' OR LENGTH(nume) > 80
                         THEN excluded.prenume ELSE prenume END""",
                (cnp, nume, prenume or ""),
            )
            cur.execute("SELECT id, cnp, nume, prenume, created_at FROM pacienti WHERE cnp = ?", (cnp,))
            return dict(cur.fetchone())
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO pacienti (cnp, nume, prenume)
            VALUES (%s, %s, %s)
            ON CONFLICT (cnp) DO UPDATE SET
              nume = CASE WHEN pacienti.nume = '' OR pacienti.nume = 'Necunoscut'
                         OR pacienti.nume LIKE '%%Medic%%' OR pacienti.nume LIKE '%%Varsta%%'
                         OR pacienti.nume LIKE '%%pacient%%' OR pacienti.nume LIKE '%%beneficiar%%'
                         OR LENGTH(pacienti.nume) > 80
                   THEN EXCLUDED.nume ELSE pacienti.nume END,
              prenume = CASE WHEN pacienti.nume = '' OR pacienti.nume = 'Necunoscut'
                         OR pacienti.nume LIKE '%%Medic%%' OR pacienti.nume LIKE '%%Varsta%%'
                         OR pacienti.nume LIKE '%%pacient%%' OR pacienti.nume LIKE '%%beneficiar%%'
                         OR LENGTH(pacienti.nume) > 80
                   THEN EXCLUDED.prenume ELSE pacienti.prenume END
            RETURNING id, cnp, nume, prenume, created_at
            """,
            (cnp, nume, prenume or ""),
        )
        return dict(cur.fetchone())


def get_pacient_by_cnp(cnp: str) -> Optional[dict]:
    with get_cursor() as cur:
        if _use_sqlite():
            cur.execute("SELECT id, cnp, nume, prenume, created_at FROM pacienti WHERE cnp = ?", (cnp,))
        else:
            cur.execute("SELECT id, cnp, nume, prenume, created_at FROM pacienti WHERE cnp = %s", (cnp,))
        row = cur.fetchone()
        return _row_to_dict(row) if row else None


# --- Buletine ---
def insert_buletin(pacient_id: int, data_buletin=None, laborator: Optional[str] = None, fisier_original: Optional[str] = None) -> dict:
    with get_cursor() as cur:
        if _use_sqlite():
            cur.execute(
                "INSERT INTO buletine (pacient_id, data_buletin, laborator, fisier_original) VALUES (?, ?, ?, ?)",
                (pacient_id, data_buletin, laborator, fisier_original),
            )
            cur.execute("SELECT id, pacient_id, data_buletin, laborator, fisier_original, created_at FROM buletine ORDER BY id DESC LIMIT 1")
            return dict(cur.fetchone())
        cur.execute(
            """
            INSERT INTO buletine (pacient_id, data_buletin, laborator, fisier_original)
            VALUES (%s, %s, %s, %s)
            RETURNING id, pacient_id, data_buletin, laborator, fisier_original, created_at
            """,
            (pacient_id, data_buletin, laborator, fisier_original),
        )
        return dict(cur.fetchone())


# --- Rezultate analize ---
def insert_rezultat(buletin_id: int, analiza_standard_id: Optional[int], denumire_raw: Optional[str],
                    valoare=None, valoare_text: Optional[str] = None, unitate: Optional[str] = None,
                    interval_min=None, interval_max=None, flag: Optional[str] = None) -> dict:
    with get_cursor() as cur:
        if _use_sqlite():
            cur.execute(
                """INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag),
            )
            cur.execute("SELECT id, buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, created_at FROM rezultate_analize ORDER BY id DESC LIMIT 1")
            return dict(cur.fetchone())
        cur.execute(
            """
            INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, created_at
            """,
            (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag),
        )
        return dict(cur.fetchone())


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
        return row[0] if _use_sqlite() else row["analiza_standard_id"]


# --- Lista si cautare pacienti ---
def get_all_pacienti() -> list:
    with get_cursor(commit=False) as cur:
        if _use_sqlite():
            cur.execute(
                "SELECT p.id, p.cnp, p.nume, p.prenume, p.created_at, COUNT(b.id) as nr_buletine "
                "FROM pacienti p LEFT JOIN buletine b ON b.pacient_id = p.id "
                "GROUP BY p.id ORDER BY p.nume"
            )
        else:
            cur.execute(
                "SELECT p.id, p.cnp, p.nume, p.prenume, p.created_at, COUNT(b.id) as nr_buletine "
                "FROM pacienti p LEFT JOIN buletine b ON b.pacient_id = p.id "
                "GROUP BY p.id ORDER BY p.nume"
            )
        return [_row_to_dict(r) for r in cur.fetchall()]


def search_pacienti(q: str) -> list:
    q_like = f"%{q}%"
    with get_cursor(commit=False) as cur:
        if _use_sqlite():
            cur.execute(
                "SELECT p.id, p.cnp, p.nume, p.prenume, p.created_at, COUNT(b.id) as nr_buletine "
                "FROM pacienti p LEFT JOIN buletine b ON b.pacient_id = p.id "
                "WHERE p.cnp LIKE ? OR LOWER(p.nume) LIKE LOWER(?) "
                "GROUP BY p.id ORDER BY p.nume",
                (q_like, q_like),
            )
        else:
            cur.execute(
                "SELECT p.id, p.cnp, p.nume, p.prenume, p.created_at, COUNT(b.id) as nr_buletine "
                "FROM pacienti p LEFT JOIN buletine b ON b.pacient_id = p.id "
                "WHERE p.cnp LIKE %s OR LOWER(p.nume) LIKE LOWER(%s) "
                "GROUP BY p.id ORDER BY p.nume",
                (q_like, q_like),
            )
        return [_row_to_dict(r) for r in cur.fetchall()]


# --- Lista analize standard ---
def get_all_analize_standard() -> list:
    with get_cursor(commit=False) as cur:
        cur.execute("SELECT id, cod_standard, denumire_standard FROM analiza_standard ORDER BY denumire_standard")
        return [_row_to_dict(r) for r in cur.fetchall()]


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
                    "SELECT id, denumire_raw, aparitii, aprobata, analiza_standard_id, created_at, updated_at "
                    "FROM analiza_necunoscuta WHERE aprobata = 0 ORDER BY aparitii DESC, denumire_raw"
                )
            else:
                cur.execute(
                    "SELECT id, denumire_raw, aparitii, aprobata, analiza_standard_id, created_at, updated_at "
                    "FROM analiza_necunoscuta ORDER BY aprobata, aparitii DESC"
                )
        else:
            q = "SELECT * FROM analiza_necunoscuta" + (" WHERE aprobata=0" if doar_neaprobate else "") + " ORDER BY aparitii DESC"
            cur.execute(q)
        return [_row_to_dict(r) for r in cur.fetchall()]


def sterge_analiza_necunoscuta(id_necunoscuta: int) -> bool:
    """Sterge o intrare din analiza_necunoscuta (ex: dupa ce a fost aprobata sau ignorata)."""
    with get_cursor() as cur:
        if _use_sqlite():
            cur.execute("DELETE FROM analiza_necunoscuta WHERE id = ?", (id_necunoscuta,))
        else:
            cur.execute("DELETE FROM analiza_necunoscuta WHERE id = %s", (id_necunoscuta,))
    return True


def get_historicul_analiza_by_cod(cod_standard: str) -> list:
    with get_cursor(commit=False) as cur:
        if _use_sqlite():
            cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = ?", (cod_standard,))
        else:
            cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = %s", (cod_standard,))
        row = cur.fetchone()
        if not row:
            return []
        aid = row[0] if _use_sqlite() else row["id"]
    return get_historicul_analiza(aid)


# --- GET /pacient/{cnp} ---
def get_pacient_cu_analize(cnp: str) -> Optional[dict]:
    pacient = get_pacient_by_cnp(cnp)
    if not pacient:
        return None
    with get_cursor() as cur:
        if _use_sqlite():
            cur.execute("SELECT id, pacient_id, data_buletin, laborator, fisier_original, created_at FROM buletine WHERE pacient_id = ? ORDER BY created_at DESC", (pacient["id"],))
        else:
            cur.execute(
                "SELECT id, pacient_id, data_buletin, laborator, fisier_original, created_at FROM buletine WHERE pacient_id = %s ORDER BY created_at DESC",
                (pacient["id"],),
            )
        buletine = [_row_to_dict(r) for r in cur.fetchall()]
    for b in buletine:
        with get_cursor() as cur:
            if _use_sqlite():
                cur.execute(
                    """SELECT r.id, r.buletin_id, r.analiza_standard_id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate, r.interval_min, r.interval_max, r.flag, r.created_at, a.cod_standard, a.denumire_standard
                    FROM rezultate_analize r LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id WHERE r.buletin_id = ? ORDER BY a.denumire_standard, r.denumire_raw""",
                    (b["id"],),
                )
            else:
                cur.execute(
                    """
                    SELECT r.id, r.buletin_id, r.analiza_standard_id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate, r.interval_min, r.interval_max, r.flag, r.created_at, a.cod_standard, a.denumire_standard
                    FROM rezultate_analize r LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id WHERE r.buletin_id = %s ORDER BY a.denumire_standard, r.denumire_raw
                    """,
                    (b["id"],),
                )
            b["rezultate"] = [_row_to_dict(r) for r in cur.fetchall()]
    pacient["buletine"] = buletine
    return pacient
