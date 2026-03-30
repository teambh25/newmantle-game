"""Integration tests for StatRepository query methods.

Suites 13-14 from docs/user-stats/test-plan.md.
Data is prepared via direct hset (not record methods) to test parsing independently.
"""

import datetime

import pytest
import pytest_asyncio

from app.features.common.redis_keys import RedisStatKeys
from app.features.stats.dto import QuizResultEntry
from tests.integration.stats.conftest import cleanup_stat_keys

TEST_USER_A = "00000000-0000-0000-0000-00000000000a"
TEST_DATE = datetime.date(2026, 3, 12)

# ---------------------------------------------------------------------------
# Suite 13: fetch_stat
# ---------------------------------------------------------------------------


class TestFetchStat:
    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_keys(self, redis_client):
        await cleanup_stat_keys(redis_client, [TEST_USER_A], [TEST_DATE])
        yield
        await cleanup_stat_keys(redis_client, [TEST_USER_A], [TEST_DATE])

    @pytest.mark.asyncio
    async def test_full_fields(self, redis_repo, redis_client):
        key = RedisStatKeys.from_user_and_date(TEST_USER_A, TEST_DATE).key
        await redis_client.hset(
            key, mapping={"status": "FAIL", "guesses": "2", "hints": "1"}
        )

        result = await redis_repo.fetch_stat(TEST_USER_A, TEST_DATE)

        assert result == QuizResultEntry(status="FAIL", guess_count=2, hint_count=1)

    @pytest.mark.asyncio
    async def test_success(self, redis_repo, redis_client):
        key = RedisStatKeys.from_user_and_date(TEST_USER_A, TEST_DATE).key
        await redis_client.hset(
            key, mapping={"status": "SUCCESS", "guesses": "3", "hints": "2"}
        )

        result = await redis_repo.fetch_stat(TEST_USER_A, TEST_DATE)

        assert result == QuizResultEntry(status="SUCCESS", guess_count=3, hint_count=2)

    @pytest.mark.asyncio
    async def test_no_record_returns_none(self, redis_repo):
        result = await redis_repo.fetch_stat(TEST_USER_A, TEST_DATE)

        assert result is None

    @pytest.mark.asyncio
    async def test_missing_hint_defaults_to_zero(self, redis_repo, redis_client):
        key = RedisStatKeys.from_user_and_date(TEST_USER_A, TEST_DATE).key
        await redis_client.hset(key, mapping={"status": "SUCCESS", "guesses": "1"})

        result = await redis_repo.fetch_stat(TEST_USER_A, TEST_DATE)

        assert result == QuizResultEntry(status="SUCCESS", guess_count=1, hint_count=0)

    @pytest.mark.asyncio
    async def test_missing_guess_defaults_to_zero(self, redis_repo, redis_client):
        key = RedisStatKeys.from_user_and_date(TEST_USER_A, TEST_DATE).key
        await redis_client.hset(key, mapping={"status": "FAIL", "hints": "1"})

        result = await redis_repo.fetch_stat(TEST_USER_A, TEST_DATE)

        assert result == QuizResultEntry(status="FAIL", guess_count=0, hint_count=1)

    @pytest.mark.asyncio
    async def test_missing_all_counts_default_to_zero(self, redis_repo, redis_client):
        key = RedisStatKeys.from_user_and_date(TEST_USER_A, TEST_DATE).key
        await redis_client.hset(key, mapping={"status": "GIVEUP"})

        result = await redis_repo.fetch_stat(TEST_USER_A, TEST_DATE)

        assert result == QuizResultEntry(status="GIVEUP", guess_count=0, hint_count=0)


# ---------------------------------------------------------------------------
# Suite 14: fetch_recent_stats
# ---------------------------------------------------------------------------

DAYS = 3

SUITE_14_DATES = [
    TEST_DATE,  # day 0 (within range)
    TEST_DATE - datetime.timedelta(days=1),  # -1 day (within range)
    TEST_DATE - datetime.timedelta(days=2),  # -2 days (within range, boundary)
    TEST_DATE - datetime.timedelta(days=3),  # -3 days (outside range, boundary)
    TEST_DATE - datetime.timedelta(days=4),  # -4 days (outside range)
]


class TestFetchRecentStats:
    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_keys(self, redis_client):
        await cleanup_stat_keys(redis_client, [TEST_USER_A], SUITE_14_DATES)
        yield
        await cleanup_stat_keys(redis_client, [TEST_USER_A], SUITE_14_DATES)

    @pytest.mark.asyncio
    async def test_only_queries_within_days_range(self, redis_repo, redis_client):
        """All 5 dates (day 0 ~ -4) have data, but only day 0 ~ -2 should be returned."""
        for d in SUITE_14_DATES:
            key = RedisStatKeys.from_user_and_date(TEST_USER_A, d).key
            await redis_client.hset(key, mapping={"status": "SUCCESS", "guesses": "1"})

        result = await redis_repo.fetch_recent_stats(TEST_USER_A, TEST_DATE, days=DAYS)

        assert len(result) == 3
        assert set(result.keys()) == {
            SUITE_14_DATES[0],  # day 0
            SUITE_14_DATES[1],  # -1
            SUITE_14_DATES[2],  # -2
        }

    @pytest.mark.asyncio
    async def test_no_records(self, redis_repo):
        result = await redis_repo.fetch_recent_stats(TEST_USER_A, TEST_DATE, days=DAYS)

        assert result == {}
