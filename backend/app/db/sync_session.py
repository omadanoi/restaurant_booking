"""Synchronous engine/session for Celery workers.

Celery's prefork/solo worker model doesn't mix with asyncio sessions, so
background tasks use a plain sync SQLAlchemy stack against the same models
(decided in Phase 1 — see docs/architecture.md).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

sync_engine = create_engine(get_settings().SYNC_DATABASE_URL, pool_pre_ping=True)

SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, expire_on_commit=False, class_=Session)
