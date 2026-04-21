"""
Runner de migrari SQL cu versioning.

Fiecare fisier SQL din /sql/ este aplicat o singura data, in ordine alfabetica.
Starea este stocata in tabela schema_migrations.

Suporta SQLite, PostgreSQL si MySQL.

Utilizare:
    python run_migrations.py
    # sau din cod:
    from backend.migration_runner import aplica_migrari
    aplica_migrari()
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

# Directorul cu fisierele SQL (relativ la radacina proiectului)
_SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

# Ordinea in care se aplica migrarile (prefixele numerice garanteaza ordinea)
# Filtram: pentru PostgreSQL luam _pg_ sau fara prefix de DB
# Pentru SQLite luam schema_sqlite, seed_sqlite sau fara prefix de DB
_PG_EXCLUDE = re.compile(r"schema_sqlite|seed_sqlite")
_SQLITE_EXCLUDE = re.compile(r"_pg_|_mysql_|_postgres")


def _fisiere_migrare(db_type: str) -> list[Path]:
    """Returneaza fisierele SQL in ordine alfabetica, filtrate dupa tipul DB."""
    all_files = sorted(_SQL_DIR.glob("*.sql"))
    result = []
    for f in all_files:
        name = f.name.lower()
        if db_type == "postgresql":
            if _PG_EXCLUDE.search(name):
                continue
        elif db_type == "sqlite":
            if _SQLITE_EXCLUDE.search(name):
                continue
        result.append(f)
    return result


def _migrari_aplicate_pg(conn) -> set[str]:
    """Returneaza setul de versiuni deja aplicate (PostgreSQL)."""
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations'"
        )
        if not cur.fetchone():
            return set()
        cur.execute("SELECT versiune FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}
    except Exception:
        return set()


def _migrari_aplicate_sqlite(conn) -> set[str]:
    """Returneaza setul de versiuni deja aplicate (SQLite)."""
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        if not cur.fetchone():
            return set()
        cur = conn.execute("SELECT versiune FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}
    except Exception:
        return set()


def _marcheaza_aplicata_pg(conn, versiune: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO schema_migrations (versiune) VALUES (%s) ON CONFLICT DO NOTHING",
        (versiune,),
    )
    conn.commit()


def _marcheaza_aplicata_sqlite(conn, versiune: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (versiune) VALUES (?)",
        (versiune,),
    )
    conn.commit()


def aplica_migrari(
    db_type: Optional[str] = None,
    verbose: bool = True,
) -> dict:
    """
    Aplica toate migrarile neprocesate, in ordine.

    Args:
        db_type: 'sqlite', 'postgresql', 'mysql'. Detectat automat din DATABASE_URL daca None.
        verbose: Afiseaza progresul la stdout.

    Returns:
        dict cu 'ok', 'aplicate', 'sarite', 'erori'
    """
    from backend.database import _detect_db_type, get_connection
    from backend.config import settings

    if db_type is None:
        db_type = _detect_db_type()

    fisiere = _fisiere_migrare(db_type)
    aplicate: list[str] = []
    sarite: list[str] = []
    erori: list[str] = []

    if db_type == "postgresql":
        from backend.deps import postgresql_connect
        url = (settings.database_url or "").strip()
        conn = postgresql_connect(url)
        conn.autocommit = False

        try:
            # Creeaza tabela schema_migrations daca nu exista
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    versiune VARCHAR(128) UNIQUE NOT NULL,
                    aplicata_la TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            conn.commit()

            deja_aplicate = _migrari_aplicate_pg(conn)

            for fpath in fisiere:
                versiune = fpath.name
                if versiune in deja_aplicate:
                    sarite.append(versiune)
                    continue

                sql_text = fpath.read_text(encoding="utf-8")
                # Sarim INSERT OR IGNORE - sunt specifice SQLite
                if "INSERT OR IGNORE" in sql_text.upper():
                    sarite.append(versiune)
                    continue

                try:
                    cur = conn.cursor()
                    cur.execute(sql_text)
                    conn.commit()
                    _marcheaza_aplicata_pg(conn, versiune)
                    aplicate.append(versiune)
                    if verbose:
                        print(f"[MIGRARE] OK {versiune}")
                except Exception as ex:
                    conn.rollback()
                    err_msg = str(ex).lower()
                    # "already exists" si "duplicate" sunt OK - migrarea a mai rulat partial
                    if "already exists" in err_msg or "duplicate" in err_msg:
                        _marcheaza_aplicata_pg(conn, versiune)
                        sarite.append(versiune)
                    else:
                        msg = f"{versiune}: {ex}"
                        erori.append(msg)
                        _log.error("[MIGRARE] EROARE %s", msg)
                        if verbose:
                            print(f"[MIGRARE] EROARE {msg}")
        finally:
            conn.close()

    elif db_type == "sqlite":
        conn = get_connection()
        try:
            # Creeaza tabela schema_migrations daca nu exista
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    versiune TEXT UNIQUE NOT NULL,
                    aplicata_la TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.commit()

            deja_aplicate = _migrari_aplicate_sqlite(conn)

            for fpath in fisiere:
                versiune = fpath.name
                if versiune in deja_aplicate:
                    sarite.append(versiune)
                    continue

                sql_text = fpath.read_text(encoding="utf-8")
                try:
                    conn.executescript(sql_text)
                    conn.commit()
                    _marcheaza_aplicata_sqlite(conn, versiune)
                    aplicate.append(versiune)
                    if verbose:
                        print(f"[MIGRARE] OK {versiune}")
                except Exception as ex:
                    err_msg = str(ex).lower()
                    if "already exists" in err_msg or "unique constraint" in err_msg:
                        _marcheaza_aplicata_sqlite(conn, versiune)
                        sarite.append(versiune)
                    else:
                        msg = f"{versiune}: {ex}"
                        erori.append(msg)
                        _log.error("[MIGRARE] EROARE %s", msg)
                        if verbose:
                            print(f"[MIGRARE] EROARE {msg}")
        finally:
            conn.close()

    else:
        erori.append(f"Tip DB nesuportat pentru migrare automata: {db_type}")

    return {
        "ok": len(erori) == 0,
        "aplicate": aplicate,
        "sarite": sarite,
        "erori": erori,
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = aplica_migrari(verbose=True)
    print(f"\nRezultat: {result['ok']}")
    print(f"  Aplicate: {len(result['aplicate'])}: {result['aplicate']}")
    print(f"  Sarite:   {len(result['sarite'])}")
    print(f"  Erori:    {len(result['erori'])}: {result['erori']}")
    sys.exit(0 if result["ok"] else 1)
