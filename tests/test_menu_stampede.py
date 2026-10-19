import asyncio

from httpx import ASGITransport, AsyncClient

from app.core.redis import redis_client
from app.main import app


async def test_cold_cache_rebuilt_once_under_concurrency(query_counter):
    await redis_client.delete("store:2:menu")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        responses = await asyncio.gather(
            *[client.get("/v1/stores/2/menu") for _ in range(50)]
        )

    assert all(r.status_code == 200 for r in responses)
    assert len({str(r.json()) for r in responses}) == 1   # everyone got the same menu
    assert query_counter["n"] == 2                        # ONE rebuild: store + products