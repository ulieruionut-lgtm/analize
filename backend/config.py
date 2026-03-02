"""Setări aplicație (env)."""
from pathlib import Path

from pydantic_settings import BaseSettings

# .env este în rădăcina proiectului (cu un nivel deasupra backend/)
_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT / ".env"

# Fișier SQLite în rădăcina proiectului – fără configurare
_DEFAULT_DB = _ROOT / "analize.db"


class Settings(BaseSettings):
    # SQLite (default), PostgreSQL sau MySQL
    # sqlite = fișier local (ideal pentru dev/test)
    # postgresql:// = PostgreSQL (ideal pentru producție)
    # mysql:// = MySQL
    database_url: str = "sqlite"  # Default: SQLite (nu necesită configurare!)
    ocr_lang: str = "ron"
    pdf_text_min_chars: int = 200
    jwt_secret_key: str = "dev-secret-change-in-production-2026"

    @property
    def db_path(self) -> Path:
        """Calea către fișierul SQLite (folosit când database_url e gol sau sqlite)."""
        if self.database_url and not self.database_url.strip().lower().startswith("sqlite"):
            return None  # PostgreSQL
        return _DEFAULT_DB

    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"


settings = Settings()

# Aplicația folosește doar PostgreSQL (nu SQLite local)
_url = (settings.database_url or "").strip().lower()
if not _url or _url.startswith("sqlite") or _url.endswith(".db"):
    import sys
    print("\n" + "=" * 60)
    print("EROARE: Aplicația folosește doar PostgreSQL.")
    print("Setează DATABASE_URL în .env sau rulează cu:")
    print("  railway run python run_migrations.py")
    print("  railway run python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000")
    print("=" * 60 + "\n")
    sys.exit(1)
