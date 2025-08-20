from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.common.config import Configs
from app.cores.redis import create_redis_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    configs = Configs()
    app.state.configs = configs
    app.state.redis_pool = create_redis_pool(configs.redis_url, configs.max_connection)
    yield
    await app.state.redis_pool.aclose()