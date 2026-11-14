from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL must be configured before using the database")
    engine = create_async_engine(database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def get_database_engine() -> AsyncEngine | None:
    if get_session_factory.cache_info().currsize == 0:
        return None
    engine = get_session_factory().kw["bind"]
    return engine if isinstance(engine, AsyncEngine) else None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        yield session


async def dispose_database_engine() -> None:
    engine = get_database_engine()
    if engine is not None:
        await engine.dispose()
    get_session_factory.cache_clear()
