from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.cores.config import configs
from app.cores.database import create_db_engine, create_session_factory, create_tables
from app.cores.logging import setup_logging
from app.cores.redis import create_redis_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    app.state.redis_pool = create_redis_pool(configs.redis_url, configs.redis_max_conn)
    app.state.db_engine = create_db_engine(
        configs.database_url, configs.db_pool_size, configs.db_max_overflow
    )
    await create_tables(app.state.db_engine)
    app.state.db_session_factory = create_session_factory(app.state.db_engine)
    yield
    await app.state.db_engine.dispose()
    await app.state.redis_pool.aclose()
