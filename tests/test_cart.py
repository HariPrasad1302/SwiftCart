from httpx import ASGITransport, AsyncClient

from app.core.redis import redis_client
from app.main import app

USER = {"X-User-Id": "9001"}


async def test_cart_roundtrip_and_read_uses_no_db_queries(query_counter):
    await redis_client.delete("cart:9001")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for pid in range(1, 11):
            r = await client.put(f"/v1/cart/items/{pid}", json={"qty": 2}, headers=USER)
            assert r.status_code == 200

        before = query_counter["n"]
        r = await client.get("/v1/cart", headers=USER)

    body = r.json()
    assert len(body["items"]) == 10
    assert body["total"] == sum(i["price"] * i["qty"] for i in body["items"])
    assert query_counter["n"] == before                        # served from Redis only
    assert 0 < await redis_client.ttl("cart:9001") <= 7 * 24 * 3600


async def test_cart_remove_and_unknown_product():
    await redis_client.delete("cart:9001")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.put("/v1/cart/items/1", json={"qty": 1}, headers=USER)).status_code == 200
        assert (await client.put("/v1/cart/items/999999", json={"qty": 1}, headers=USER)).status_code == 404
        assert (await client.delete("/v1/cart/items/1", headers=USER)).status_code == 200
        body = (await client.get("/v1/cart", headers=USER)).json()

    assert body["items"] == []
    assert body["total"] == 0