import json
import random

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