import os

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/test")
os.environ.setdefault("DB_POOL_SIZE", "5")
os.environ.setdefault("DB_MAX_OVERFLOW", "10")
os.environ.setdefault("DB_POOL_TIMEOUT", "30")
os.environ.setdefault("DB_ECHO", "false")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("SESSION_TIMEOUT", "86400")
os.environ.setdefault("AUTH_SERVICE_URL", "http://auth.test")
os.environ.setdefault("AUTH_SERVICE_API_KEY", "test-key")
os.environ.setdefault("AUTH_SERVICE_TIMEOUT", "30")
os.environ.setdefault("EPG_SERVICE_URL", "http://epg.test")
os.environ.setdefault("EPG_SERVICE_TIMEOUT", "30")
os.environ.setdefault("EPG_SERVICE_FETCH_TIMEOUT", "300")
os.environ.setdefault("RUTV_SITE_URL", "http://rutv.test")
os.environ.setdefault("RUTV_STATS_TOKEN", "test-token")
os.environ.setdefault("RUTV_SITE_TIMEOUT", "30")
os.environ.setdefault("BASE_URL", "http://playlist.test")
os.environ.setdefault("PAGINATION_DEFAULT_PER_PAGE", "20")
os.environ.setdefault("PAGINATION_MAX_PER_PAGE", "100")
os.environ.setdefault("LOOKUP_DEFAULT_LIMIT", "50")
os.environ.setdefault("LOOKUP_MAX_LIMIT", "1000")
os.environ.setdefault("TOKEN_LENGTH", "32")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("INTEGRATION_API_KEY", "integration-test-key")

from app.models import Base


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()
