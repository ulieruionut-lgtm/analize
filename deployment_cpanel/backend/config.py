"""Setări aplicație (env)."""
from pathlib import Path

from pydantic_settings import BaseSettings

# .env este în rădăcina proiectului (cu un nivel deasupra backend/)
_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT / ".env"

# Fișier SQLite în rădăcina proiectului – fără configurare
_DEFAULT_DB = _ROOT / "analize.db"


class Settings(BaseSettings):
    # Gol sau sqlite = folosește fișierul analize.db (fără configurare). Altfel = PostgreSQL.
    database_url: str = "sqlite"
    ocr_lang: str = "ron"
    pdf_text_min_chars: int = 200

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
