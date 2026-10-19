from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.db import get_db
from app.modules.catalog.models import Store, Product, Review
from fastapi import APIRouter, Query, Depends, HTTPException
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
    store = (await db.execute(select(Store).where(Store.id == store_id))).scalar_one_or_none()
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")

    products = (await db.execute(
        select(Product).where(Product.store_id == store_id, Product.is_active))).scalars().all()

    return {
        "store": {"id": store.id, "name": store.name},
        "items": [{"id": p.id, "name": p.name, "price": p.price} for p in products],
    }