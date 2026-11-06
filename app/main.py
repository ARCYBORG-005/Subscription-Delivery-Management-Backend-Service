from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.routes import router
from app.core.database import Base, engine
from app.db import models  # noqa: F401 - register ORM tables with Base.metadata


@asynccontextmanager
async def lifespan(_: FastAPI):
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Milk Delivery Optimizer",
    description="Order and zone-aware milk delivery routing API.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
