import pytest_asyncio
from sqlalchemy import Column, Table, Uuid, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cores.config import configs
from app.cores.database import create_db_engine
from app.features.common.redis_keys import RedisStatKeys
from app.features.stats.repository import StatRepository
from app.models.models import Base

# redis_client fixture is defined in tests/integration/conftest.py

# Stub table for auth.users (Supabase auth) to satisfy FK constraints in tests.
# Uses Table directly instead of a model class to avoid duplicate class warnings.
if "auth.users" not in Base.metadata.tables:
    Table("users", Base.metadata, Column("id", Uuid, primary_key=True), schema="auth")

# ---------------------------------------------------------------------------
# Redis fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def redis_repo(redis_client):
    """StatRepository with real Redis only (no DB session)."""
    return StatRepository(session=None, redis_client=redis_client)


# ---------------------------------------------------------------------------
# DB fixtures (lazy — only activated when a test requests repo or db_session)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_engine():
    if not configs.test_database_url:
        raise RuntimeError("TEST_DATABASE_URL is required for integration tests")
    engine = create_db_engine(
        configs.test_database_url,
        pool_size=configs.db_pool_size,
        max_overflow=configs.db_max_overflow,
    )
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
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


async def cleanup_user_stat_keys(redis_client, user_ids, dates):
    """Helper to delete Redis stat keys for given user/date combinations."""
    for u in user_ids:
        for d in dates:
            key = RedisStatKeys.from_user_and_date(u, d).key
            await redis_client.delete(key)


async def cleanup_guest_stat_keys(redis_client, guest_ids, dates):
    """Helper to delete Redis guest stat keys for given guest/date combinations."""
    for g in guest_ids:
        for d in dates:
            key = RedisStatKeys.from_guest_and_date(g, d).key
            await redis_client.delete(key)


async def seed_auth_users(db_session, user_ids):
    """Insert stub rows into auth.users to satisfy FK constraints."""
    for uid in user_ids:
        await db_session.execute(
            text("INSERT INTO auth.users (id) VALUES (:id) ON CONFLICT DO NOTHING"),
            {"id": uid},
        )
    await db_session.flush()
