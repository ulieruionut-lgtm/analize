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
    # OCR Tesseract: PSM 3=auto table, OEM 2=LSTM+legacy, ron+eng pentru termeni medicali
    ocr_lang: str = "ron+eng"
    ocr_psm: int = 3   # 3=auto segmentare (bun pt tabele), 4=coloană, 6=bloc, 11=sparse
    ocr_oem: int = 2   # 1=LSTM, 2=LSTM+legacy (tessdata full are ambele)
    ocr_psm_fallback: int = 4   # retry cu acest PSM dacă rezultat < ocr_min_chars
    ocr_psm_sparse: int = 11    # ultimă încercare: text sparse (buletine cu liste)
    ocr_min_chars: int = 100    # prag pentru retry cu PSM fallback
    ocr_dpi_hint: int = 400     # transmis Tesseract ca user_defined_dpi (aliniat cu rasterizarea)
    # TESSDATA_PREFIX: setează în .env pt tessdata_best (mai precis, mai lent). Ex: /usr/share/tessdata_best
    tessdata_prefix: str | None = None
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

# Pe Railway: daca DATABASE_URL lipsește, pornim cu SQLite temporar ca healthcheck sa treaca.
# Setează DATABASE_URL (PostgreSQL) în Variables pentru productie.
_url = (settings.database_url or "").strip().lower()
if not _url or _url.startswith("sqlite") or _url.endswith(".db"):
    print("\n[CONFIG] DATABASE_URL neconfigurat - folosim SQLite. Setează DATABASE_URL (PostgreSQL) pentru productie.\n")
