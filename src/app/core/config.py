from __future__ import annotations

from functools import lru_cache
from pydantic import BaseSettings, AnyUrl


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    ENV: str = "development"
    DEBUG: bool = False

    DATABASE_URL: AnyUrl
    TEST_DATABASE_URL: AnyUrl | None = None

    REDIS_URL: AnyUrl | None = None

    RESEND_API_KEY: str | None = None
    EMAIL_FROM_ADDRESS: str | None = None

    class Config:
        env_file = ".env"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

