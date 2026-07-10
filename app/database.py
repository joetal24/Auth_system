from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        pass  # ponytail: silent startup, add health check logging if needed


async def close_db():
    await engine.dispose()


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        yield session