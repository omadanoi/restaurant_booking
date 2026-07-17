from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.session import get_db

settings = get_settings()

# Tests always run against a dedicated *_test database (created by
# infra/postgres/init.sql) — never the dev database, and never SQLite,
# since the reservation overlap constraint needs real GiST/btree_gist support.
TEST_DATABASE_URL = settings.DATABASE_URL.rsplit("/", 1)[0] + "/restaurant_platform_test"
TEST_SYNC_DATABASE_URL = settings.SYNC_DATABASE_URL.rsplit("/", 1)[0] + "/restaurant_platform_test"

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_SYNC_DATABASE_URL)
    return cfg


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> Generator[None, None, None]:
    """Runs the real Alembic migration chain once per test session.

    This validates the migration itself (not just `create_all`), which
    matters here specifically because the overlap-prevention EXCLUDE
    constraint is applied via a hand-written `op.execute` in 0001, not
    something a generic `create_all` would reproduce.
    """
    command.upgrade(_alembic_config(), "head")
    yield
    command.downgrade(_alembic_config(), "base")


# Function-scoped on purpose: each test runs in its own event loop
# (pytest-asyncio default), and an asyncpg pool must not be shared across
# loops. Engine construction is lazy, so per-test creation is cheap.
@pytest_asyncio.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    eng = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """One test = one outer transaction + a SAVEPOINT that's restarted after
    every flush/commit inside the test, all rolled back at teardown. Lets
    service-layer code call `session.commit()` normally without tests
    leaking data into each other. See SQLAlchemy's async join-a-transaction
    testing recipe.
    """
    connection = await engine.connect()
    outer_transaction = await connection.begin()
    await connection.begin_nested()

    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    @event.listens_for(session.sync_session, "after_transaction_end")
    def _restart_savepoint(sync_session, transaction) -> None:
        if connection.closed:
            return
        if not connection.sync_connection.in_nested_transaction():
            connection.sync_connection.begin_nested()

    try:
        yield session
    finally:
        await session.close()
        await outer_transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from app.main import app

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
