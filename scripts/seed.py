import random

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.catalog.models import Product, Review, Store

engine = create_engine(settings.database_url.replace("+asyncpg", "+psycopg2"))

STORES, PRODUCTS_PER_STORE, REVIEWS_PER_STORE = 200, 50, 20
random.seed(42)

with Session(engine) as db:
    db.execute(text("TRUNCATE reviews, products, stores RESTART IDENTITY CASCADE"))

    stores = [
        Store(
            name=f"Store {i}",
            lat=13.08 + random.uniform(-0.1, 0.1),
            lon=80.27 + random.uniform(-0.1, 0.1),
        )
        for i in range(1, STORES + 1)
    ]

    db.add_all(stores)
    db.flush()

    for s in stores:
        db.add_all(
            Product(
                store_id=s.id,
                name=f"Item {j}",
                price=random.uniform(2000, 50000),
            )
            for j in range(1, PRODUCTS_PER_STORE + 1)
        )
        db.add_all(
            Review(
                store_id=s.id,
                rating=random.randint(1, 5),
            )
            for _ in range(REVIEWS_PER_STORE)
        )

    db.commit()
    
    print(f"Seeded {STORES} stores, {STORES * PRODUCTS_PER_STORE} products, and {STORES * REVIEWS_PER_STORE} reviews.")