import json
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    PROJECT_NAME: str = "Restaurant Reservation & Table Management Platform"
    API_V1_STR: str = "/api/v1"

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "restaurant_platform"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/restaurant_platform"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/restaurant_platform"

    REDIS_URL: str = "redis://localhost:6379/0"

    # Notifications (Phase 5). "logged" writes structured logs + DB rows;
    # a future real sender (e.g. "smtp") plugs in via the same setting
    # without touching call sites (ADR 0003).
    NOTIFICATION_SENDER: str = "logged"
    REMINDER_LEAD_HOURS: int = 24

    # Booking-deposit payments. "demo" settles instantly with no external
    # calls; a real provider (planned: a Kyrgyz PSP) plugs in via the same
    # setting without touching call sites — see app/payments/base.py.
    PAYMENT_PROVIDER: str = "demo"

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # Accepts either a JSON array or a comma-separated list, because hosting
    # dashboards are a hostile place to type JSON.
    CORS_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        raw = value.strip()
        if raw.startswith("["):
            return json.loads(raw)
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _derive_database_urls(self) -> "Settings":
        """Make a managed host's plain DSN usable as-is.

        Providers hand out one `postgresql://user:pass@host/db` URL, but this
        app needs two: asyncpg for the app and psycopg2 for Alembic. Fill in
        the drivers rather than making the operator write both by hand. An
        explicitly-set SYNC_DATABASE_URL still wins.
        """
        scheme, sep, rest = self.DATABASE_URL.partition("://")
        if sep and scheme in ("postgres", "postgresql"):
            self.DATABASE_URL = f"postgresql+asyncpg://{rest}"
        if "SYNC_DATABASE_URL" not in self.model_fields_set:
            _, _, rest = self.DATABASE_URL.partition("://")
            self.SYNC_DATABASE_URL = f"postgresql+psycopg2://{rest}"
        return self

    @model_validator(mode="after")
    def _require_production_secret(self) -> "Settings":
        if self.ENV == "production" and self.SECRET_KEY == "change-me-in-production":
            raise ValueError(
                "SECRET_KEY must be set to a random value when ENV=production "
                "(the default would let anyone forge access tokens)."
            )
        return self

    @property
    def is_development(self) -> bool:
        return self.ENV == "development"

    @property
    def is_testing(self) -> bool:
        return self.ENV == "testing"


@lru_cache
def get_settings() -> Settings:
    return Settings()
