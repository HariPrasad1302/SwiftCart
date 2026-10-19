from httpx import ASGITransport, AsyncClient

from app.core.redis import redis_client
from app.main import app


async def test_menu_second_call_served_from_cache(query_counter):
    await redis_client.delete("store:1:menu")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.get("/v1/stores/1/menu")
        after_first = query_counter["n"]
        r2 = await client.get("/v1/stores/1/menu")

    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()
    assert after_first == 2                      # miss: store + products
    assert query_counter["n"] == after_first     # hit: zero extra queries
    assert await redis_client.ttl("store:1:menu") > 0   # has an expiry