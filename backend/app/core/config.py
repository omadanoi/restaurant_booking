from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    @property
    def is_development(self) -> bool:
        return self.ENV == "development"

    @property
    def is_testing(self) -> bool:
        return self.ENV == "testing"


@lru_cache
def get_settings() -> Settings:
    return Settings()
