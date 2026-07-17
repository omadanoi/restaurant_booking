from app.core.config import Settings, get_settings


def test_settings_load_with_defaults() -> None:
    settings = Settings()

    assert settings.PROJECT_NAME
    assert settings.API_V1_STR.startswith("/")
    assert settings.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert settings.SYNC_DATABASE_URL.startswith("postgresql+psycopg2://")


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
