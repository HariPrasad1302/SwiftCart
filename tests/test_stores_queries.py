from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_list_stores_query_count(query_counter):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/v1/stores")
    assert r.status_code == 200
    assert len(r.json()) == 50
    assert query_counter["n"] <= 3, f"N+1 detected: {query_counter['n']} queries"