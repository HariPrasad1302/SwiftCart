from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_keyset_pagination_walks_every_store_once(query_counter):
    seen = []
    pages = 0
    cursor = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        while True:
            params = {"limit": 60}
            if cursor is not None:
                params["cursor"] = cursor
            r = await client.get("/v1/stores", params=params)
            assert r.status_code == 200
            body = r.json()
            seen += [s["id"] for s in body["items"]]
            pages += 1
            cursor = body["next_cursor"]
            if cursor is None:
                break

    assert seen == sorted(set(seen))       # no duplicates, in order
    assert len(seen) == 200                # every seeded store, exactly once
    assert query_counter["n"] == pages     # exactly one query per page