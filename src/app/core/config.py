from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import AnyUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Environment
    ENV: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: AnyUrl
    TEST_DATABASE_URL: Optional[AnyUrl] = None

    # Redis/Queue
    REDIS_URL: Optional[AnyUrl] = None

    # Authentication (Phase 2 - FastAPI)
    SECRET_KEY: str  # Required for JWT signing
    ALGORITHM: str = "HS256"  # JWT algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Token expiration in minutes

    # Email (Resend)
    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM_ADDRESS: Optional[str] = None

    # AI Providers
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # File Storage
    UPLOAD_FOLDER: Optional[str] = None
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = "pdf,docx,doc,jpg,png"

    # Application
    APP_NAME: str = "Junior Counsel"
    APP_URL: str = "http://localhost:8000"

    # CORS (Phase 2 - FastAPI)
    CORS_ORIGINS: str = "http://localhost:3000"  # Comma-separated frontend URLs

    # Uvicorn (Development)
    RELOAD: bool = True  # Auto-reload on code changes

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins from environment variable."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

