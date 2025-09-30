from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.cores.config import configs
from app.cores.logging import setup_logging
from app.cores.redis import create_redis_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    app.state.redis_pool = create_redis_pool(configs.redis_url, configs.max_connection)
    yield
    await app.state.redis_pool.aclose()
