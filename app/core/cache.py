import json
import random
import time
import uuid
import asyncio

from redis.exceptions import RedisError
from app.core.redis import redis_client

async def cache_get(key: str):
    try:
        raw = await redis_client.get(key)
    except RedisError:
        return None
    return json.loads(raw) if raw else None

async def cache_set(key: str, value, ttl: int) -> None:
    ttl += random.randint(0, ttl//10)
    try:
        await redis_client.set(key, json.dumps(value), ex=ttl)
    except RedisError:
        pass

async def cache_delete(key: str) -> None:
    try:
        await redis_client.delete(key)
    except RedisError:
        pass

_RELEASE_LOCK = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""

async def get_or_build(key: str, ttl: int, builder, lock_ms: int = 5000, wait_s: float = 2.0):
    cached = await cache_get(key)
    if cached is not None:
        return cached

    lock_key = f"lock:{key}"
    token = uuid.uuid4().hex
    try:
        got_lock = await redis_client.set(lock_key, token, nx=True, px=lock_ms)
    except RedisError:
        return await builder()                    # Redis down: just hit the DB

    if got_lock:
        try:
            value = await builder()
            await cache_set(key, value, ttl)
            return value
        finally:
            try:
                await redis_client.eval(_RELEASE_LOCK, 1, lock_key, token)
            except RedisError:
                pass

    # someone else is rebuilding: poll the cache briefly
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        await asyncio.sleep(0.05)
        cached = await cache_get(key)
        if cached is not None:
            return cached
    return await builder() 