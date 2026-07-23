from redis.asyncio import Redis
from app.config import settings


redis_client: Redis | None = None


async def get_redis() -> Redis | None:
    global redis_client
    if redis_client is not None:
        try:
            await redis_client.ping()
            return redis_client
        except Exception:
            redis_client = None
    try:
        redis_client = await Redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
    except Exception:
        redis_client = None
    return redis_client


async def close_redis():
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


async def blacklist_token(jti: str, expires_in: int):
    r = await get_redis()
    if r is None:
        return
    await r.set(f"blacklist:{jti}", "true", ex=expires_in)


async def is_token_blacklisted(jti: str) -> bool:
    r = await get_redis()
    if r is None:
        return False
    return bool(await r.exists(f"blacklist:{jti}"))


async def set_value(key: str, value: str, expires_in: int) -> None:
    r = await get_redis()
    if r is None:
        raise RuntimeError("Redis not available")
    await r.set(key, value, ex=expires_in)


async def get_value(key: str) -> str | None:
    r = await get_redis()
    if r is None:
        raise RuntimeError("Redis not available")
    val = await r.get(key)
    return val.decode() if val else None


async def delete_value(key: str) -> None:
    r = await get_redis()
    if r is None:
        raise RuntimeError("Redis not available")
    await r.delete(key)


