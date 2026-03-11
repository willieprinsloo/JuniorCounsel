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

    # Authentication
    SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

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

    class Config:
        env_file = ".env"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

