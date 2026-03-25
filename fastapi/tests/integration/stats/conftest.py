import pytest_asyncio
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cores.config import configs
from app.cores.database import create_db_engine
from app.features.common.redis_keys import RedisStatKeys
from app.features.stats.repository import StatRepository
from app.models.models import Base

# ---------------------------------------------------------------------------
# Redis fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def redis_client():
    client = redis.from_url(configs.redis_url, decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def redis_repo(redis_client):
    """StatRepository with real Redis only (no DB session)."""
    return StatRepository(session=None, redis_client=redis_client)


# ---------------------------------------------------------------------------
# DB fixtures (lazy — only activated when a test requests repo or db_session)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_engine():
    engine = create_db_engine(
        configs.database_url,
        pool_size=configs.db_pool_size,
        max_overflow=configs.db_max_overflow,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Session bound to a transaction that is rolled back after each test.

    Uses SQLAlchemy's join_transaction_mode so that session.commit()
    inside production code releases a SAVEPOINT instead of the real
    transaction.  The outer transaction is rolled back in cleanup,
    leaving the DB untouched.
    """
    async with db_engine.connect() as conn:
        txn = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        yield session
        await session.close()
        await txn.rollback()


@pytest_asyncio.fixture
async def repo(redis_client, db_session):
    """StatRepository with real Redis and real DB session."""
    return StatRepository(session=db_session, redis_client=redis_client)


# ---------------------------------------------------------------------------
# Cleanup helpers
# ---------------------------------------------------------------------------


async def cleanup_stat_keys(redis_client, user_ids, dates):
    """Helper to delete Redis stat keys for given user/date combinations."""
    for u in user_ids:
        for d in dates:
            key = RedisStatKeys.from_user_and_date(u, d).key
            await redis_client.delete(key)
