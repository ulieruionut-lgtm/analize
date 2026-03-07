"""Conexiune SQLite (implicit), PostgreSQL sau MySQL. CRUD pentru MVP."""
import sqlite3
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
        d = dict(row)
    else:
        d = dict(zip([c[0] for c in row.description], row))
    # Convertim datetime/date la string ISO (PostgreSQL le returneaza ca obiecte Python)
    for k, v in d.items():
        if isinstance(v, (datetime, date)):
            d[k] = v.isoformat()
    return d


# --- Pacienti ---
def upsert_pacient(cnp: str, nume: str, prenume: Optional[str] = None) -> dict:
    if _use_sqlite():
        with get_cursor() as cur:
            cur.execute(
                "INSERT INTO pacienti (cnp, nume, prenume) VALUES (?, ?, ?) ON CONFLICT(cnp) DO UPDATE SET nume=excluded.nume, prenume=excluded.prenume",
                (cnp, nume, prenume or ""),
            )
            cur.execute("SELECT id, cnp, nume, prenume, created_at FROM pacienti WHERE cnp = ?", (cnp,))
            return dict(cur.fetchone())
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO pacienti (cnp, nume, prenume)
            VALUES (%s, %s, %s)
            ON CONFLICT (cnp) DO UPDATE SET nume = EXCLUDED.nume, prenume = EXCLUDED.prenume
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
                    interval_min=None, interval_max=None, flag: Optional[str] = None,
                    ordine: Optional[int] = None, categorie: Optional[str] = None) -> dict:
    with get_cursor() as cur:
        if _use_sqlite():
            cur.execute(
                """INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie),
            )
            cur.execute("SELECT id, buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie, created_at FROM rezultate_analize ORDER BY id DESC LIMIT 1")
            return dict(cur.fetchone())
        cur.execute(
            """
            INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie, created_at
            """,
            (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate, interval_min, interval_max, flag, ordine, categorie),
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
                    """SELECT r.id, r.buletin_id, r.analiza_standard_id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate, r.interval_min, r.interval_max, r.flag, r.ordine, r.categorie, r.created_at, a.cod_standard, a.denumire_standard
                    FROM rezultate_analize r LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id WHERE r.buletin_id = ? ORDER BY COALESCE(r.ordine, 99999), a.denumire_standard, r.denumire_raw""",
                    (b["id"],),
                )
            else:
                cur.execute(
                    """
                    SELECT r.id, r.buletin_id, r.analiza_standard_id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate, r.interval_min, r.interval_max, r.flag, r.ordine, r.categorie, r.created_at, a.cod_standard, a.denumire_standard
                    FROM rezultate_analize r LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id WHERE r.buletin_id = %s ORDER BY COALESCE(r.ordine, 99999), a.denumire_standard NULLS LAST, r.denumire_raw
                    """,
                    (b["id"],),
                )
            b["rezultate"] = [_row_to_dict(r) for r in cur.fetchall()]
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
        if _use_sqlite():
            cur.execute("SELECT COUNT(*) FROM users")
            cnt = cur.fetchone()[0]
        else:
            cur.execute("SELECT COUNT(*) FROM users")
            row = cur.fetchone()
            cnt = list(row.values())[0] if row else 0
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
    except Exception:
        return False


# --- Editare manuala rezultate ---

def get_rezultate_buletin(buletin_id: int) -> list:
    """Returneaza toate rezultatele unui buletin, cu denumire_standard si flag."""
    try:
        with get_cursor(commit=False) as cur:
            ph = "?" if _use_sqlite() else "%s"
            cur.execute(f"""
                SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate, r.flag,
                       r.interval_min, r.interval_max,
                       r.analiza_standard_id, r.ordine, r.categorie,
                       a.denumire_standard, a.cod_standard
                FROM rezultate_analize r
                LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
                WHERE r.buletin_id = {ph}
                ORDER BY COALESCE(r.ordine, 99999), a.denumire_standard NULLS LAST, r.denumire_raw
            """, (buletin_id,))
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
        with get_cursor() as cur:
            ph = "?" if _use_sqlite() else "%s"
            cur.execute(f"""
                INSERT INTO rezultate_analize
                    (buletin_id, analiza_standard_id, denumire_raw, valoare, unitate, flag)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph})
                RETURNING id
            """, (buletin_id, analiza_standard_id, denumire_raw.strip(), valoare, unitate, flag or None))
            row = cur.fetchone()
            if row is None:
                return None
            # RealDictCursor (PostgreSQL) returneaza dict, sqlite returneaza tuple
            row_id = row["id"] if hasattr(row, "keys") else row[0]
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
        cur.execute(
            """SELECT id, buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text,
                      unitate, interval_min, interval_max, flag, created_at
               FROM rezultate_analize ORDER BY id"""
        )
        out["rezultate_analize"] = [_json_serializable(_row_to_dict(r)) for r in cur.fetchall()]
    return out
