"""
TalentLens AI — application configuration.
All values can be overridden via environment variables or a .env file.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "TalentLens AI"
    VERSION: str = "2.0.0"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ── Security ─────────────────────────────────────────────────────────────
    # NOTE: In production `SECRET_KEY` must be provided via env/secret manager.
    SECRET_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Hosts allowed to serve traffic (TrustedHost middleware). Keep tight in prod.
    ALLOWED_HOSTS: List[str] = ["localhost"]
    # CORS origins (frontend domains). Keep tight in prod.
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # ── MongoDB ───────────────────────────────────────────────────────────────
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "talentlens"

    # ── Vector DB ─────────────────────────────────────────────────────────────
    CHROMA_PERSIST_DIRECTORY: str = Field(
        "./data/vector_db/chroma",
        validation_alias=AliasChoices("CHROMA_PERSIST_DIR", "CHROMA_PERSIST_DIRECTORY"),
    )

    # ── ML ────────────────────────────────────────────────────────────────────
    MODEL_PATH: str = "./data/models/model.pkl"
    VECTORIZER_PATH: str = "./data/models/vectorizer.pkl"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # ── Data ──────────────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./data/uploads"
    EXPORT_DIR: str = "./data/exports"
    CACHE_DIR: str = "./data/cache"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg", ".tif", ".tiff"]
    SKIP_HF_DATASET: bool = False

    # ── AI / LLM ──────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""

    # ── Operational ──────────────────────────────────────────────────────────
    # Whether to enforce strict startup validation (set False for some test runners)
    STRICT_STARTUP_CHECKS: bool = True

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()


def _validate_settings(s: Settings) -> None:
    """Perform runtime validation and fail-fast for missing critical values."""
    if not s.DEBUG and s.STRICT_STARTUP_CHECKS:
        missing = []
        if not s.SECRET_KEY:
            missing.append("SECRET_KEY")
        if not s.ALLOWED_ORIGINS or s.ALLOWED_ORIGINS == ["*"]:
            missing.append("ALLOWED_ORIGINS (must not be wildcard '*')")
        if missing:
            raise RuntimeError(f"Missing or insecure environment settings: {', '.join(missing)}")


# Run validation now so the app fails fast on misconfiguration
try:
    _validate_settings(settings)
except Exception as exc:
    # When tests or interactive sessions import settings we don't always want to abort.
    # Re-raise only when STRICT_STARTUP_CHECKS is True and not in DEBUG mode.
    if settings.STRICT_STARTUP_CHECKS and not settings.DEBUG:
        raise