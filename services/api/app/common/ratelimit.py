"""Fixed-window rate limits in Redis. Each endpoint family uses its own bucket name."""

from app.common.errors import RateLimited
from app.common.redis import get_redis


async def hit(bucket: str, key: str, *, limit: int, window_seconds: int) -> None:
    """Count one request; raise RateLimited once `limit` is exceeded within the window."""
    redis = get_redis()
    rkey = f"rl:{bucket}:{key}"
    pipe = redis.pipeline()
    pipe.incr(rkey)
    pipe.expire(rkey, window_seconds, nx=True)
    pipe.ttl(rkey)
    count, _, ttl = await pipe.execute()
    if int(count) > limit:
        raise RateLimited(retry_after=max(int(ttl), 1))
