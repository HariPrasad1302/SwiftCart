from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.modules.cart import service
from app.modules.catalog.service import get_products

router = APIRouter(prefix="/v1/cart", tags=["cart"])


def current_user_id(x_user_id: int = Header(...)) -> int:
    return x_user_id        # TEMPORARY: replaced by JWT auth in Level 4


class QtyBody(BaseModel):
    qty: int = Field(ge=1, le=20)


@router.get("")
async def view_cart(user_id: int = Depends(current_user_id), db: AsyncSession = Depends(get_db)):
    return await service.get_cart(db, user_id)


@router.put("/items/{product_id}")
async def put_item(
    product_id: int,
    body: QtyBody,
    user_id: int = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if product_id not in await get_products(db, [product_id]):
        raise HTTPException(status_code=404, detail="Product not found")
    await service.set_item(user_id, product_id, body.qty)
    return {"product_id": product_id, "qty": body.qty}


@router.delete("/items/{product_id}")
async def delete_item(product_id: int, user_id: int = Depends(current_user_id)):
    await service.remove_item(user_id, product_id)
    return {"removed": product_id}