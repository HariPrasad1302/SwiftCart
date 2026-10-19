import json
import random

from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.modules.catalog.models import Product


async def get_products(db: AsyncSession, ids: list[int]) -> dict[int, dict]:
    """Many products with one MGET; only the misses touch the DB (one query)."""
    if not ids:
        return {}

    try:
        raw = await redis_client.mget([f"product:{i}" for i in ids])
    except RedisError:
        raw = [None] * len(ids)

    found, missing = {}, []
    for pid, value in zip(ids, raw):
        if value:
            found[pid] = json.loads(value)
        else:
            missing.append(pid)

    if missing:
        rows = (await db.execute(
            select(Product).where(Product.id.in_(missing), Product.is_active)
        )).scalars().all()
        fetched = {
            p.id: {"id": p.id, "store_id": p.store_id, "name": p.name, "price": p.price}
            for p in rows
        }
        try:
            async with redis_client.pipeline() as pipe:        # write all misses in one trip
                for pid, data in fetched.items():
                    pipe.set(f"product:{pid}", json.dumps(data), ex=600 + random.randint(0, 60))
                await pipe.execute()
        except RedisError:
            pass
        found.update(fetched)

    return found