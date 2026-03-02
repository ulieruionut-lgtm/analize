"""
Script de testare conexiune bază de date.
Testează conectarea la SQLite, PostgreSQL sau MySQL bazat pe DATABASE_URL.
"""
import sys
import os
import io

# Fix encoding pentru Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Adaugă backend la path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from config import settings
from database import get_connection, _detect_db_type

def test_connection():
    print("="*60)
    print("TEST CONEXIUNE BAZA DE DATE")
    print("="*60)
    
    db_type = _detect_db_type()
    print(f"\nOK - Tip baza de date detectat: {db_type.upper()}")
    print(f"OK - DATABASE_URL: {settings.database_url[:50]}..." if len(settings.database_url) > 50 else f"OK - DATABASE_URL: {settings.database_url}")
    
    try:
        print("\n-> Incerc conectarea...")
        conn = get_connection()
        print("OK - Conexiune reusita!")
        
        # Test query simplu
        cur = conn.cursor()
        
        if db_type == "sqlite":
            cur.execute("SELECT sqlite_version()")
            version = cur.fetchone()[0]
            print(f"OK - SQLite versiune: {version}")
        elif db_type == "mysql":
            cur.execute("SELECT VERSION()")
            version = cur.fetchone()['VERSION()']
            print(f"OK - MySQL versiune: {version}")
        elif db_type == "postgresql":
            cur.execute("SELECT version()")
            version = cur.fetchone()['version']
            print(f"OK - PostgreSQL versiune: {version[:50]}...")
        
        # Test tabele
        print("\n-> Verific tabelele...")
        if db_type == "sqlite":
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cur.fetchall()]
        elif db_type == "mysql":
            cur.execute("SHOW TABLES")
            tables = [list(row.values())[0] for row in cur.fetchall()]
        elif db_type == "postgresql":
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
            tables = [row['tablename'] for row in cur.fetchall()]
        
        if tables:
            print(f"OK - Tabele gasite: {', '.join(tables)}")
            
            # Test count pacienti
            cur.execute("SELECT COUNT(*) as cnt FROM pacienti")
            if db_type == "sqlite":
                count = cur.fetchone()[0]
            else:
                count = cur.fetchone()['cnt']
            print(f"OK - Numar pacienti in baza de date: {count}")
        else:
            print("ATENTIE - Nicio tabela gasita - rulati run_migrations.py")
        
        cur.close()
        conn.close()
        
        print("\n" + "="*60)
        print("OK - TOATE TESTELE AU TRECUT!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\nEROARE: {e}")
        print("\nVerificati:")
        print("1. DATABASE_URL este corect in .env")
        print("2. Baza de date este pornita si accesibila")
        print("3. Credentialele sunt corecte")
        print("4. Tabelele sunt create (rulati run_migrations.py)")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
