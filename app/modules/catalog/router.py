from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import math
from redis.exceptions import RedisError
from app.core.redis import redis_client

from app.core.db import get_db
from app.modules.catalog.models import Store, Product, Review
from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel, Field
from app.core.cache import cache_get, cache_set,cache_delete, get_or_build
router = APIRouter(prefix="/v1/stores", tags=["stores"])


@router.get("")
async def list_stores(limit: int = Query(50, ge=1, le=100), cursor: int | None = Query(None, ge=1), db: AsyncSession = Depends(get_db)):
    # stores = (await db.execute(select(Store).limit(50))).scalars().all()

    # result = []
    # for s in stores:
    #     avg = (await db.execute(select(
    #         func.avg(Review.rating)).where(
    #             Review.store_id == s.id))).scalar()

    #     reviews = (await db.execute(
    #         select(func.count()).select_from(Review).where(Review.store_id == s.id)
    #     )).scalar()
    #     products = (await db.execute(
    #         select(func.count()).select_from(Product).where(Product.store_id == s.id)
    #     )).scalar()

    #     result.append({
    #         "id": s.id,
    #         "name": s.name,
    #         "avg_rating": round(float(avg or 0), 2),
    #         "review_count": reviews,
    #         "product_count": products,
    #     })
    result = dict()
    avg_rating = (
        select(func.coalesce(func.avg(Review.rating),0))
        .where(Review.store_id == Store.id)
        .scalar_subquery()
    )

    review_count = (
        select(func.count())
        .where(Review.store_id == Store.id)
        .scalar_subquery()
    )
    product_count = (
        select(func.count())
        .where(Product.store_id == Store.id)
        .scalar_subquery()
    )

    stmt = (
        select(
            Store.id,
            Store.name,
            avg_rating.label("avg_rating"),
            review_count.label("review_count"),
            product_count.label("product_count"),
        )
        .order_by(Store.id)
        .limit(50)
    )
    if cursor is not None:
        stmt = stmt.where(Store.id > cursor)

    stmt = stmt.order_by(Store.id).limit(limit + 1)

    store_rows = (await db.execute(stmt)).all()

    has_more = len(store_rows) > limit
    store_rows = store_rows[:limit]

    result["items"] = [
        {
            "id": s.id,
            "name": s.name,
            "avg_rating": round(float(s.avg_rating), 2),
            "review_count": s.review_count,
            "product_count": s.product_count,
        }
        for s in store_rows
    ]
    result["next_cursor"] = store_rows[-1].id if has_more else None


    return result


@router.get("/{store_id}/menu")
async def store_menu(store_id: int, db: AsyncSession = Depends(get_db)):
    async def build():
        store = (await db.execute(
            select(Store).where(Store.id == store_id))).scalar_one_or_none()
        if store is None:
            raise HTTPException(status_code=404, detail="Store not found")

        products = (await db.execute(
            select(Product)
            .where(Product.store_id == store_id, Product.is_active)
            .order_by(Product.id)
        )).scalars().all()

        return {
            "store": {"id": store.id, "name": store.name},
            "items": [{"id": p.id, "name": p.name, "price": p.price} for p in products],
        }

    return await get_or_build(f"store:{store_id}:menu", ttl=300, builder=build)


class PriceUpdate(BaseModel):
    price: int = Field(gt=0)


@router.patch("/{store_id}/products/{product_id}")
@router.patch("/{store_id}/products/{product_id}")
async def update_price(
    store_id: int,
    product_id: int,
    body: PriceUpdate,
    db: AsyncSession = Depends(get_db),
):
    product = (await db.execute(
        select(Product).where(Product.id == product_id, Product.store_id == store_id)
    )).scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product.price = body.price
    await db.commit()
    await cache_delete(f"store:{store_id}:menu")
    await cache_delete(f"product:{product_id}") 

    return {"id": product.id, "price": product.price}


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(a))


@router.get("/nearby")
async def nearby_stores(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(5, gt=0, le=50),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    try:
        hits = await redis_client.geosearch(
            "stores:geo", longitude=lng, latitude=lat,
            radius=radius_km, unit="km", sort="ASC", count=limit, withdist=True,
        )
        distances = {int(member): float(dist) for member, dist in hits}
    except RedisError:
        # degrade: scan stores in the DB and compute distances in Python (slower)
        all_stores = (await db.execute(select(Store.id, Store.lat, Store.lng))).all()
        scored = sorted(
            (_haversine_km(lat, lng, s.lat, s.lng), s.id) for s in all_stores
        )
        distances = {sid: d for d, sid in scored if d <= radius_km}
        distances = dict(list(distances.items())[:limit])

    if not distances:
        return {"items": []}

    rows = (await db.execute(
        select(Store.id, Store.name, Store.is_open).where(Store.id.in_(distances))
    )).all()
    by_id = {r.id: r for r in rows}

    return {
        "items": [
            {"id": sid, "name": by_id[sid].name, "is_open": by_id[sid].is_open,
             "distance_km": round(dist, 3)}
            for sid, dist in distances.items() if sid in by_id
        ]
    }