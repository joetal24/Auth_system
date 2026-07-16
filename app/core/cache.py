from redis.asyncio import Redis
from app.config import settings


# Global Redis client (singleton pattern)
redis_client: Redis | None = None

async def get_redis() -> Redis:
    """Get or create the global Redis client."""
    global redis_client
    if redis_client is None:
        redis_client = await Redis.from_url(settings.REDIS_URL)
    return redis_client

async def close_redis():
    """Close the global Redis client."""
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()


async def blacklist_token(jti: str, expires_in: int):
    """Add a token ID to the blacklist for the specified duration."""
    r = await get_redis()
    await r.set(f"blacklist:{jti}", "true", ex=expires_in)


async def is_token_blacklisted(jti: str) -> bool:
    """Check if a token ID is blacklisted."""
    r = await get_redis()
    return bool(await r.exists(f"blacklist:{jti}"))


