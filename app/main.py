from fastapi import FastAPI
from app.core.config import settings
from app.modules.catalog.router import router as catalog_router

app = FastAPI(title="SwiftCart", version="0.1.0")
app.include_router(catalog_router)

@app.get("/")
async def root():
    return {"message": "Welcome to SwiftCart!"}

@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}