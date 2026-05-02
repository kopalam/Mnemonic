"""Database connection and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mnemonic.config import config

# Async engine
engine = create_async_engine(
    config.async_database_url,
    pool_size=config["database"]["pool_size"],
    max_overflow=config["database"]["max_overflow"],
    echo=config.get("api", {}).get("debug", False),
)

# Session factory
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI endpoints."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for non-FastAPI usage."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize database (create tables if not exist)."""
    from mnemonic.models import Base
    
    async with engine.begin() as conn:
        # 先创建pgvector扩展
        await conn.execute(__import__('sqlalchemy').text('CREATE EXTENSION IF NOT EXISTS vector'))
        await conn.commit()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
