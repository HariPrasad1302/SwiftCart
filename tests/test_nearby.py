from httpx import ASGITransport, AsyncClient

from app.core.redis import redis_client
from app.main import app


async def test_nearby_returns_closest_first(query_counter):
    (lng, lat), = await redis_client.geopos("stores:geo", "1")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/v1/stores/nearby", params={"lat": lat, "lng": lng, "radius_km": 3})

    assert r.status_code == 200
    items = r.json()["items"]
    assert items[0]["id"] == 1                       # standing on store 1: it's closest
    assert items[0]["distance_km"] < 0.1
    dists = [i["distance_km"] for i in items]
    assert dists == sorted(dists)                    # nearest first
    assert query_counter["n"] <= 1                   # one DB query, however many results


async def test_nearby_far_away_is_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/v1/stores/nearby", params={"lat": 0, "lng": 0, "radius_km": 5})
    assert r.json()["items"] == []