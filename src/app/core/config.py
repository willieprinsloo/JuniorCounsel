from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

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
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]  # Frontend URLs

    # Uvicorn (Development)
    RELOAD: bool = True  # Auto-reload on code changes

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

        @staticmethod
        def parse_env_var(field_name: str, raw_val: str):
            """Parse environment variables, especially lists."""
            if field_name == "CORS_ORIGINS":
                return [origin.strip() for origin in raw_val.split(",")]
            return raw_val


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

