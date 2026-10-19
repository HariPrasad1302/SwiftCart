from httpx import ASGITransport, AsyncClient

from app.core.redis import redis_client
from app.main import app


async def test_price_edit_invalidates_menu_cache():
    await redis_client.delete("store:1:menu")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        menu = (await client.get("/v1/stores/1/menu")).json()        # fills the cache
        item = menu["items"][0]
        old_price, new_price = item["price"], item["price"] + 100

        try:
            r = await client.patch(
                f"/v1/stores/1/products/{item['id']}", json={"price": new_price}
            )
            assert r.status_code == 200
            assert await redis_client.exists("store:1:menu") == 0    # key was deleted

            fresh = (await client.get("/v1/stores/1/menu")).json()
            assert fresh["items"][0]["price"] == new_price           # no stale price
        finally:
            await client.patch(                                      # restore seed data
                f"/v1/stores/1/products/{item['id']}", json={"price": old_price}
            )