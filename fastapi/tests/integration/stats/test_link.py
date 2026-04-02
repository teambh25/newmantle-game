"""Integration tests for guest→user stat linking via StatRepository."""

import datetime

import pytest
import pytest_asyncio

from app.features.common.redis_keys import RedisStatKeys
from tests.integration.stats.conftest import (
    cleanup_guest_stat_keys,
    cleanup_user_stat_keys,
)

TODAY = datetime.date(2026, 4, 1)
USER_ID = "00000000-0000-0000-0000-000000000001"
GUEST_ID = "00000000-0000-0000-0000-000000000002"

GUEST_STAT_DATA = {"status": "SUCCESS", "guesses": "3", "hints": "1"}
USER_STAT_DATA = {"status": "FAIL", "guesses": "5", "hints": "0"}

_TTL_DATES = [TODAY - datetime.timedelta(days=i) for i in range(RedisStatKeys.TTL_DAYS)]


async def seed_guest(redis_client, date: datetime.date):
    await redis_client.hset(
        RedisStatKeys.from_guest_and_date(GUEST_ID, date).key, mapping=GUEST_STAT_DATA
    )


async def seed_user(redis_client, date: datetime.date):
    await redis_client.hset(
        RedisStatKeys.from_user_and_date(USER_ID, date).key, mapping=USER_STAT_DATA
    )


async def key_exists(redis_client, key: str) -> bool:
    return await redis_client.exists(key) == 1


class TestLinkGuestStats:
    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self, redis_client):
        await cleanup_user_stat_keys(redis_client, [USER_ID], _TTL_DATES)
        await cleanup_guest_stat_keys(redis_client, [GUEST_ID], _TTL_DATES)
        yield
        await cleanup_user_stat_keys(redis_client, [USER_ID], _TTL_DATES)
        await cleanup_guest_stat_keys(redis_client, [GUEST_ID], _TTL_DATES)

    @pytest.mark.asyncio
    async def test_renames_guest_key_to_user_key(self, redis_repo, redis_client):
        await seed_guest(redis_client, TODAY)

        await redis_repo.link_guest_stats(USER_ID, GUEST_ID, TODAY)

        assert not await key_exists(
            redis_client, RedisStatKeys.from_guest_and_date(GUEST_ID, TODAY).key
        )
        data = await redis_client.hgetall(
            RedisStatKeys.from_user_and_date(USER_ID, TODAY).key
        )
        assert data["status"] == GUEST_STAT_DATA["status"]

    @pytest.mark.asyncio
    async def test_deletes_guest_key_when_user_key_already_exists(
        self, redis_repo, redis_client
    ):
        await seed_user(redis_client, TODAY)
        await seed_guest(redis_client, TODAY)

        await redis_repo.link_guest_stats(USER_ID, GUEST_ID, TODAY)

        assert not await key_exists(
            redis_client, RedisStatKeys.from_guest_and_date(GUEST_ID, TODAY).key
        )
        # User key must be unchanged
        data = await redis_client.hgetall(
            RedisStatKeys.from_user_and_date(USER_ID, TODAY).key
        )
        assert data["status"] == USER_STAT_DATA["status"]

    @pytest.mark.asyncio
    async def test_skips_date_when_guest_key_absent(self, redis_repo, redis_client):
        await redis_repo.link_guest_stats(USER_ID, GUEST_ID, TODAY)

        assert not await key_exists(
            redis_client, RedisStatKeys.from_user_and_date(USER_ID, TODAY).key
        )

    @pytest.mark.asyncio
    async def test_mixed_dates(self, redis_repo, redis_client):
        date0 = TODAY
        date1 = TODAY - datetime.timedelta(days=1)

        await seed_guest(redis_client, date0)  # no user key → linked
        await seed_guest(redis_client, date1)
        await seed_user(redis_client, date1)  # user key exists → guest deleted

        await redis_repo.link_guest_stats(USER_ID, GUEST_ID, TODAY)

        # date0: guest renamed to user
        assert not await key_exists(
            redis_client, RedisStatKeys.from_guest_and_date(GUEST_ID, date0).key
        )
        assert await key_exists(
            redis_client, RedisStatKeys.from_user_and_date(USER_ID, date0).key
        )
        # date1: guest deleted, user unchanged
        assert not await key_exists(
            redis_client, RedisStatKeys.from_guest_and_date(GUEST_ID, date1).key
        )
        data = await redis_client.hgetall(
            RedisStatKeys.from_user_and_date(USER_ID, date1).key
        )
        assert data["status"] == USER_STAT_DATA["status"]
