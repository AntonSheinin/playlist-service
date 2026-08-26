import asyncio
import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.exceptions import PlaylistServiceError

logger = logging.getLogger(__name__)

settings = get_settings()

engine = create_async_engine(
    settings.async_database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    echo=settings.db_echo,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            await session.rollback()
            raise
        except PlaylistServiceError as error:
            await session.rollback()
            log = logger.debug if error.status_code < 500 else logger.error
            log("Request failed, rolling back transaction: %s", error)
            raise
        except Exception as e:
            await session.rollback()
            logger.error("Request failed, rolling back transaction: %s", e)
            raise
