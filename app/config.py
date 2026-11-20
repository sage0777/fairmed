"""
FairMed Configuration Module
Loads environment variables and application settings using Pydantic Settings.
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # App Information
    APP_NAME: str = "FairMed Medical Bill Auditing API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True

    # Security
    JWT_SECRET_KEY: str = "fairmed_secret_development_key_change_in_production_89af3b7c4d"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database
    # Defaults to local SQLite, easily overridden with Supabase PostgreSQL connection string
    DATABASE_URL: str = "sqlite:///./fairmed.db"

    # Supabase (Optional for local mode, required for Supabase cloud storage/auth)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    # Storage paths
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    REPORTS_DIR: Path = BASE_DIR / "generated_reports"
    DATASETS_DIR: Path = BASE_DIR / "datasets"

    # OCR and Processing Settings
    OCR_ENGINE: str = "hybrid"  # hybrid, pypdf, paddleocr
    MAX_FILE_SIZE_MB: int = 25

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
settings.DATASETS_DIR.mkdir(parents=True, exist_ok=True)
