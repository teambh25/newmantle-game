import datetime

import pytest
import pytest_asyncio
import redis.asyncio as redis

from app.cores.config import configs
from app.features.common.redis_keys import RedisStatKeys
from app.features.stats.repository import StatRepository

TEST_USER_A = "test-user-a"
TEST_USER_B = "test-user-b"
TEST_DATE = datetime.date(2026, 3, 12)
TEST_DATE_OTHER = datetime.date(2026, 3, 13)


@pytest_asyncio.fixture
async def redis_client():
    client = redis.from_url(configs.redis_url, decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def user_id():
    return TEST_USER_A


@pytest.fixture
def quiz_date():
    return TEST_DATE


@pytest_asyncio.fixture
async def repo(redis_client):
    """StatRepository with real Redis and dummy DB session (Phase 3 is Redis-only)."""
    return StatRepository(session=None, redis_client=redis_client)


@pytest_asyncio.fixture(autouse=True)
async def cleanup_keys(redis_client):
    """Delete test stat keys before and after each test."""
    keys_to_clean = [
        RedisStatKeys.from_user_and_date(TEST_USER_A, TEST_DATE).key,
        RedisStatKeys.from_user_and_date(TEST_USER_B, TEST_DATE).key,
        RedisStatKeys.from_user_and_date(TEST_USER_A, TEST_DATE_OTHER).key,
    ]
    for key in keys_to_clean:
        await redis_client.delete(key)
    yield
    for key in keys_to_clean:
        await redis_client.delete(key)


async def assert_stat(
    redis_client,
    user_id: str,
    date: datetime.date,
    *,
    status: str | None = None,
    guesses: int | None = None,
    hints: int | None = None,
):
    """Helper to verify Redis Hash stat fields.

    - Fields set to a value: assert the Redis field equals that value.
    - Fields set to None (default): skip verification for that field.
    - All fields None: assert the key does not exist (empty hash).
    """
    key = RedisStatKeys.from_user_and_date(user_id, date).key
    data = await redis_client.hgetall(key)

    if status is None and guesses is None and hints is None:
        assert data == {}, f"Expected empty hash, got {data}"
        return

    if status is not None:
        assert data.get("status") == status, (
            f"Expected status={status}, got {data.get('status')}"
        )

    if guesses is not None:
        assert data.get("guesses") == str(guesses), (
            f"Expected guesses={guesses}, got {data.get('guesses')}"
        )

    if hints is not None:
        assert data.get("hints") == str(hints), (
            f"Expected hints={hints}, got {data.get('hints')}"
        )
