"""Integration tests for StatRepository.flush_stats.

Suite 15 from docs/user-stats/test-plan.md.
Data is prepared via direct hset, then flushed to real PostgreSQL.
"""

import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.features.common.redis_keys import RedisStatKeys
from app.models import UserQuizResult
from tests.integration.stats.conftest import cleanup_stat_keys, seed_auth_users

TEST_USER_A = "00000000-0000-0000-0000-00000000000a"
TEST_USER_B = "00000000-0000-0000-0000-00000000000b"
TEST_USER_C = "00000000-0000-0000-0000-00000000000c"
TEST_DATE = datetime.date(2026, 3, 12)
TEST_DATE_OTHER = datetime.date(2026, 3, 13)
TEST_USER_IDS = [TEST_USER_A, TEST_USER_B, TEST_USER_C]


# ---------------------------------------------------------------------------
# Cleanup & helpers
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def cleanup(redis_client, db_session):
    """Clean up Redis keys and seed test users before each test.

    DB cleanup is handled by transaction rollback in the db_session fixture.
    """
    await seed_auth_users(db_session, TEST_USER_IDS)
    await cleanup_stat_keys(redis_client, TEST_USER_IDS, [TEST_DATE, TEST_DATE_OTHER])
    yield
    await cleanup_stat_keys(redis_client, TEST_USER_IDS, [TEST_DATE, TEST_DATE_OTHER])


async def _write_stat(redis_client, user_id, date, mapping):
    """Write a stat hash directly to Redis."""
    key = RedisStatKeys.from_user_and_date(user_id, date).key
    await redis_client.hset(key, mapping=mapping)


async def _fetch_db_row(db_session, user_id, quiz_date) -> UserQuizResult | None:
    """Fetch a single row from user_quiz_results."""
    result = await db_session.execute(
        select(UserQuizResult).where(
            UserQuizResult.user_id == user_id,
            UserQuizResult.quiz_date == quiz_date,
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Suite 15: flush basic operations
# ---------------------------------------------------------------------------


class TestFlushBasic:
    @pytest.mark.asyncio
    async def test_single_user_flush(self, repo, redis_client, db_session):
        await _write_stat(
            redis_client,
            TEST_USER_A,
            TEST_DATE,
            {"status": "FAIL", "guesses": "2", "hints": "1"},
        )

        flushed, skipped = await repo.flush_stats(TEST_DATE)

        assert (flushed, skipped) == (1, 0)
        row = await _fetch_db_row(db_session, TEST_USER_A, TEST_DATE)
        assert row is not None
        assert row.status.value == "FAIL"
        assert row.guess_count == 2
        assert row.hint_count == 1

    @pytest.mark.asyncio
    async def test_multiple_users_flush(self, repo, redis_client, db_session):
        await _write_stat(
            redis_client,
            TEST_USER_A,
            TEST_DATE,
            {"status": "SUCCESS", "guesses": "5", "hints": "2"},
        )
        await _write_stat(
            redis_client,
            TEST_USER_B,
            TEST_DATE,
            {"status": "GIVEUP", "guesses": "3", "hints": "1"},
        )
        await _write_stat(
            redis_client,
            TEST_USER_C,
            TEST_DATE,
            {"status": "FAIL", "guesses": "1"},
        )

        flushed, skipped = await repo.flush_stats(TEST_DATE)

        assert (flushed, skipped) == (3, 0)
        for uid in [TEST_USER_A, TEST_USER_B, TEST_USER_C]:
            row = await _fetch_db_row(db_session, uid, TEST_DATE)
            assert row is not None

    @pytest.mark.asyncio
    async def test_empty_redis(self, repo):
        flushed, skipped = await repo.flush_stats(TEST_DATE)

        assert (flushed, skipped) == (0, 0)

    @pytest.mark.asyncio
    async def test_idempotency(self, repo, redis_client, db_session):
        await _write_stat(
            redis_client,
            TEST_USER_A,
            TEST_DATE,
            {"status": "SUCCESS", "guesses": "3", "hints": "1"},
        )

        first = await repo.flush_stats(TEST_DATE)
        second = await repo.flush_stats(TEST_DATE)

        assert first == second
        row = await _fetch_db_row(db_session, TEST_USER_A, TEST_DATE)
        assert row is not None
        assert row.status.value == "SUCCESS"
        assert row.guess_count == 3
        assert row.hint_count == 1

    @pytest.mark.asyncio
    async def test_date_isolation(self, repo, redis_client, db_session):
        await _write_stat(
            redis_client,
            TEST_USER_A,
            TEST_DATE,
            {"status": "FAIL", "guesses": "1"},
        )
        await _write_stat(
            redis_client,
            TEST_USER_A,
            TEST_DATE_OTHER,
            {"status": "SUCCESS", "guesses": "2"},
        )

        flushed, skipped = await repo.flush_stats(TEST_DATE)

        assert (flushed, skipped) == (1, 0)
        row_flushed = await _fetch_db_row(db_session, TEST_USER_A, TEST_DATE)
        assert row_flushed is not None
        row_other = await _fetch_db_row(db_session, TEST_USER_A, TEST_DATE_OTHER)
        assert row_other is None

    @pytest.mark.asyncio
    async def test_missing_hints_default_to_zero(self, repo, redis_client, db_session):
        await _write_stat(
            redis_client,
            TEST_USER_A,
            TEST_DATE,
            {"status": "SUCCESS", "guesses": "1"},
        )

        await repo.flush_stats(TEST_DATE)

        row = await _fetch_db_row(db_session, TEST_USER_A, TEST_DATE)
        assert row is not None
        assert row.hint_count == 0

    @pytest.mark.asyncio
    async def test_missing_guesses_default_to_zero(
        self, repo, redis_client, db_session
    ):
        await _write_stat(
            redis_client,
            TEST_USER_A,
            TEST_DATE,
            {"status": "FAIL", "hints": "1"},
        )

        await repo.flush_stats(TEST_DATE)

        row = await _fetch_db_row(db_session, TEST_USER_A, TEST_DATE)
        assert row is not None
        assert row.guess_count == 0

    @pytest.mark.asyncio
    async def test_overwrite_existing(self, repo, redis_client, db_session):
        # Pre-insert old record into DB
        await _write_stat(
            redis_client,
            TEST_USER_A,
            TEST_DATE,
            {"status": "FAIL", "guesses": "1", "hints": "0"},
        )
        await repo.flush_stats(TEST_DATE)

        # Now Redis has updated data
        await _write_stat(
            redis_client,
            TEST_USER_A,
            TEST_DATE,
            {"status": "SUCCESS", "guesses": "5", "hints": "2"},
        )

        flushed, skipped = await repo.flush_stats(TEST_DATE)

        assert (flushed, skipped) == (1, 0)
        # Expire cached ORM state to re-read from DB
        db_session.expire_all()
        row = await _fetch_db_row(db_session, TEST_USER_A, TEST_DATE)
        assert row is not None
        assert row.status.value == "SUCCESS"
        assert row.guess_count == 5
        assert row.hint_count == 2
