from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.db import get_db
from app.modules.catalog.models import Store, Product, Review

router = APIRouter(prefix="/v1/stores", tags=["stores"])


@router.get("")
async def list_stores(db: AsyncSession = Depends(get_db)):
    stores = (await db.execute(select(Store).limit(50))).scalars().all()

    result = []
    for s in stores:
        avg = (await db.execute(select(
            func.avg(Review.rating)).where(
                Review.store_id == s.id))).scalar()

        reviews = (await db.execute(
            select(func.count()).select_from(Review).where(Review.store_id == s.id)
        )).scalar()
        products = (await db.execute(
            select(func.count()).select_from(Product).where(Product.store_id == s.id)
        )).scalar()

        result.append({
            "id": s.id,
            "name": s.name,
            "avg_rating": round(float(avg or 0), 2),
            "review_count": reviews,
            "product_count": products,
        })

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