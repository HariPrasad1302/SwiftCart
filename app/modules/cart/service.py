from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.modules.catalog.service import get_products

CART_TTL = 7 * 24 * 3600


def _key(user_id: int) -> str:
    return f"cart:{user_id}"


async def set_item(user_id: int, product_id: int, qty: int) -> None:
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.hset(_key(user_id), str(product_id), qty)
        pipe.expire(_key(user_id), CART_TTL)          # refresh the 7-day TTL
        await pipe.execute()


async def remove_item(user_id: int, product_id: int) -> None:
    await redis_client.hdel(_key(user_id), str(product_id))


async def get_cart(db: AsyncSession, user_id: int) -> dict:
    raw = await redis_client.hgetall(_key(user_id))               # round trip 1
    products = await get_products(db, [int(pid) for pid in raw])  # round trip 2 (MGET)

    items, total = [], 0
    for pid, qty in raw.items():
        p = products.get(int(pid))
        if p is None:                       # product removed or deactivated: skip it
            continue
        line = p["price"] * int(qty)
        total += line
        items.append({"product_id": p["id"], "name": p["name"],
                      "price": p["price"], "qty": int(qty)})
    return {"items": items, "total": total}      # total is computed server-side