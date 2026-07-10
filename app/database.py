from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with session_maker() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync()

async def close_db():
    await engine.dispose()