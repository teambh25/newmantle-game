from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.cores.config import settings
from app.cores.redis import create_redis_pool
from app.cores.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    app.state.redis_pool = create_redis_pool(settings.redis_url, settings.max_connection)
    yield
    await app.state.redis_pool.aclose()