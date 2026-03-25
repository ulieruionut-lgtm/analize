"""Setari aplicatie (env)."""
from pathlib import Path

from pydantic_settings import BaseSettings

_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT / ".env"
_DEFAULT_DB = _ROOT / "analize.db"


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite"

    # OCR Tesseract
    # OEM 3 = LSTM pur (mai rapid si precis pe Tesseract 4/5 decat OEM 2 deprecated)
    # PSM 6 = bloc uniform de text (ideal pentru tabele medicale aliniate)
    # DPI 300 = suficient pentru text medical standard (400 creste RAM fara beneficiu real)
    ocr_lang: str = "ron+eng"
    ocr_psm: int = 6
    ocr_oem: int = 3
    ocr_psm_fallback: int = 4
    ocr_psm_sparse: int = 11
    ocr_min_chars: int = 100
    ocr_dpi_hint: int = 300
    ocr_use_metrics_retry: bool = True
    ocr_retry_min_mean_conf: float = 50.0
    ocr_retry_max_weak_ratio: float = 0.40
    ocr_weak_word_conf: int = 55
    ocr_min_digit_ratio: float = 0.0
    # True = alege clean vs hard dupa contrastul imaginii (mai precis decat mereu hard)
    ocr_preprocess_auto: bool = True
    ocr_layout_auto: bool = True
    ocr_column_segmentation: bool = False

    tessdata_prefix: str | None = None
    pdf_text_min_chars: int = 200
    upload_max_mb: int = 20
    # Timeout de bază (secunde) pentru un singur pas OCR la upload; se adaugă supliment după dimensiunea fișierului.
    upload_ocr_timeout_seconds: int = 180
    upload_enable_detailed_errors: bool = False
    jwt_secret_key: str = ""

    @property
    def db_path(self) -> Path:
        if self.database_url and not self.database_url.strip().lower().startswith("sqlite"):
            return None
        return _DEFAULT_DB

    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"


settings = Settings()

_url = (settings.database_url or "").strip().lower()
if not _url or _url.startswith("sqlite") or _url.endswith(".db"):
    print("\n[CONFIG] DATABASE_URL neconfigurat - folosim SQLite. Seteaza DATABASE_URL (PostgreSQL) pentru productie.\n")

_env = (settings.app_env or "development").strip().lower()
if _env in {"prod", "production"} and not (settings.jwt_secret_key or "").strip():
    raise RuntimeError("APP_ENV=production necesită JWT_SECRET_KEY setat în environment.")
