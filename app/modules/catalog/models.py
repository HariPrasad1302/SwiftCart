from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base

class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    lat: Mapped[float]
    lon: Mapped[float]
    is_open: Mapped[bool] = mapped_column(default=True)

    products: Mapped[list["Product"]] = relationship(back_populates="store")
    reviews: Mapped[list["Review"]] = relationship(back_populates="store")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)

    store: Mapped["Store"] = relationship(back_populates="products")

class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    rating: Mapped[int]

    store: Mapped["Store"] = relationship(back_populates="reviews")
