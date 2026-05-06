"""
Exportă baza de date într-un fișier backup.
Rulează: python exporta_baza_date.py

Creează în backups/:
- analize_db_YYYY-MM-DD.json – export complet JSON (funcționează pentru SQLite și PostgreSQL)
- analize.db.YYYY-MM-DD (opțional, doar pentru SQLite local) – copie fișier .db
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Adaugă rădăcina proiectului la path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

def main():
    from backend.database import export_backup_data, _use_sqlite, _sqlite_path

    data_azi = datetime.now().strftime("%Y-%m-%d")
    backups_dir = ROOT / "backups"
    backups_dir.mkdir(exist_ok=True)

    # 1. Export JSON (funcționează pentru ambele tipuri de DB)
    print("Export date în JSON...")
    data = export_backup_data()
    json_path = backups_dir / f"analize_db_{data_azi}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  -> {json_path}")

    # 2. Dacă SQLite, copiază și fișierul .db
    if _use_sqlite():
        db_path = _sqlite_path()
        if db_path and db_path.exists():
            db_copy = backups_dir / f"analize.db.{data_azi}"
            shutil.copy2(db_path, db_copy)
            print(f"  -> {db_copy} (copie SQLite)")
        else:
            print("  (fișier SQLite inexistent - doar JSON exportat)")
    else:
        print("  (PostgreSQL - doar JSON exportat, nu există fișier .db local)")

    print("\nOK - Backup salvat in backups/")

if __name__ == "__main__":
    main()
