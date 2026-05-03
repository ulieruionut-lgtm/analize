"""Setari aplicatie (env)."""
import secrets
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT / ".env"
_DEFAULT_DB = _ROOT / "analize.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = "sqlite"

    @field_validator("database_url", mode="before")
    @classmethod
    def _postgres_sslmode_railway(cls, v):
        """Railway PostgreSQL (proxy.rlwy.net): fără sslmode, conexiunile pot pica intermitent."""
        if v is None:
            return v
        s = str(v).strip()
        low = s.lower()
        if not low.startswith("postgres"):
            return s
        if "sslmode=" in low:
            return s
        if "rlwy.net" in low or "railway.internal" in low:
            sep = "&" if "?" in s else "?"
            return f"{s}{sep}sslmode=require"
        return s

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
    # Prag minim confidence (word-level) la reconstrucția rândurilor din TSV; 20 excludea prea multe cuvinte pe scanuri slabe.
    ocr_word_conf_floor: int = 12
    ocr_min_digit_ratio: float = 0.0
    # True = alege clean vs hard dupa contrastul imaginii (mai precis decat mereu hard)
    ocr_preprocess_auto: bool = True
    ocr_layout_auto: bool = True
    # True = în reconstrucția TSV inserează tab-uri la goluri mari între cuvinte (tabele multi-coloană)
    ocr_column_segmentation: bool = True

    tessdata_prefix: str | None = None
    # Cale explicită către tesseract.exe (Windows: dacă nu e în PATH). Alternativă: variabila de mediu TESSERACT_CMD.
    tesseract_cmd: str | None = None
    pdf_text_min_chars: int = 200
    upload_max_mb: int = 20
    # Timeout de bază (secunde) pentru un singur pas OCR la upload; se adaugă supliment după dimensiunea fișierului.
    upload_ocr_timeout_seconds: int = 180
    upload_enable_detailed_errors: bool = False
    jwt_secret_key: str = ""

    # AI Copilot — audit LLM la upload (temporar, implicit oprit). Oprire: false sau fără cheie API.
    # llm_provider: openai = API compatibil OpenAI (implicit); anthropic = Claude direct (ex. Haiku).
    llm_buletin_audit_enabled: bool = False
    llm_buletin_audit_timeout_seconds: float = 90.0
    llm_provider: str = "openai"
    llm_base_url: str | None = None
    llm_model: str | None = None
    # Din ANTHROPIC_API_KEY în .env (llm_chat citește și din os.environ)
    anthropic_api_key: str | None = None

    # La reîncărcare cu aceeași dată de buletin: completează analize mapate lipsă din ultima încărcare anterioară
    prior_upload_gap_fill_enabled: bool = True

    # După normalizare: LLM + catalog pentru rânduri fără mapare; peste prag salvează alias (învățare).
    # Implicit oprit (cost + risc mapări greșite); pornești explicit în producție dacă vrei auto-alias.
    llm_learn_from_upload_enabled: bool = False
    llm_learn_auto_apply_min_score: float = 86.0
    llm_learn_max_calls_per_upload: int = 40

    # Upload async: dacă OCR+salvare depășește (PDF mare / retry DPI), job marcat error la polling.
    # Implicit 30 min (12 min e prea scurt pentru 3–5 MB scan + 2 treceri OCR). Env: UPLOAD_ASYNC_STALE_MINUTES
    upload_async_stale_minutes: int = 30

    def get_jwt_secret(self) -> str:
        """Returneaza JWT secret key. Daca nu e setat, genereaza unul random (valabil doar in procesul curent)."""
        key = (self.jwt_secret_key or "").strip()
        if key:
            return key
        # Fara secret configurat: genereaza unul ephemer si avertizeaza.
        # La restart toate sesiunile active expira - acceptabil in dev, nerecomandat in prod.
        import logging
        logging.getLogger(__name__).warning(
            "[CONFIG] JWT_SECRET_KEY nu este setat! "
            "Se foloseste o cheie generata aleator - toate sesiunile expira la restart. "
            "Seteaza JWT_SECRET_KEY in .env pentru persistenta sesiunilor."
        )
        return secrets.token_hex(32)

    @property
    def db_path(self) -> Path:
        if self.database_url and not self.database_url.strip().lower().startswith("sqlite"):
            return None
        return _DEFAULT_DB


settings = Settings()

_url = (settings.database_url or "").strip().lower()
if not _url or _url.startswith("sqlite") or _url.endswith(".db"):
    print("\n[CONFIG] DATABASE_URL neconfigurat - folosim SQLite. Seteaza DATABASE_URL (PostgreSQL) pentru productie.\n")

_env = (settings.app_env or "development").strip().lower()
if not (settings.jwt_secret_key or "").strip():
    if _env in {"prod", "production"}:
        raise RuntimeError(
            "APP_ENV=production necesită JWT_SECRET_KEY setat în environment. "
            "Genereaza cu: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    # In dev/staging: avertisment - get_jwt_secret() va genera ephemer la primul apel
    print("\n[CONFIG] ⚠️  JWT_SECRET_KEY nu este setat! Sesiunile expira la restart serverului.\n"
          "[CONFIG]     Seteaza JWT_SECRET_KEY in .env pentru persistenta sesiunilor.\n")
if _env in {"prod", "production"} and (not _url or _url.startswith("sqlite") or _url.endswith(".db")):
    print("\n[CONFIG] ⚠️  ATENTIE: APP_ENV=production dar DATABASE_URL foloseste SQLite!")
    print("[CONFIG] ⚠️  Datele NU se pastreaza intre redeploy-uri pe Railway cu SQLite!")
    print("[CONFIG] ⚠️  Seteaza DATABASE_URL=postgresql://... in variabilele Railway!\n")
