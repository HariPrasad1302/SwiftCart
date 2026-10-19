import redis
from sqlalchemy import create_engine, text

from app.core.config import settings

engine = create_engine(settings.database_url.replace("+asyncpg", "+psycopg2"))
r = redis.Redis.from_url(settings.redis_url, decode_responses=True)

with engine.connect() as conn:
    rows = conn.execute(text("SELECT id, lon, lat FROM stores")).all()

values = []
for store_id, lng, lat in rows:
    values += [lng, lat, str(store_id)]      # GEO wants: longitude, latitude, member

r.delete("stores:geo")
r.geoadd("stores:geo", values)
print(f"Loaded {len(rows)} stores into stores:geo")