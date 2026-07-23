import time
import uuid

from fastapi import Request, HTTPException, status

from app.core.cache import get_redis


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> None:
        r = await get_redis()
        if r is None:
            return
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate:{client_ip}:{request.url.path}"
        now = int(time.time())
        member = str(uuid.uuid4())
        async with r.pipeline() as pipe:
            pipe.zadd(key, {member: now})
            pipe.zremrangebyscore(key, 0, now - self.window_seconds)
            pipe.zcard(key)
            pipe.expire(key, self.window_seconds)
            _, _, count, _ = await pipe.execute()
        if count > self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
            )
