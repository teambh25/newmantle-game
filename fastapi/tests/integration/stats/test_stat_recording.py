"""Integration tests for stat recording via StatRepository."""

import datetime

import pytest
import pytest_asyncio

from app.features.common.redis_keys import RedisStatKeys
from tests.integration.stats.conftest import (
    cleanup_guest_stat_keys,
    cleanup_user_stat_keys,
)

TEST_USER_A = "00000000-0000-0000-0000-00000000000a"
TEST_USER_B = "00000000-0000-0000-0000-00000000000b"
TEST_GUEST_A = "00000000-0000-0000-0000-00000000000c"
TEST_DATE = datetime.date(2026, 3, 12)
TEST_DATE_OTHER = datetime.date(2026, 3, 13)


@pytest_asyncio.fixture(autouse=True)
async def cleanup_keys(redis_client):
    await cleanup_user_stat_keys(
        redis_client, [TEST_USER_A, TEST_USER_B], [TEST_DATE, TEST_DATE_OTHER]
    )
    yield
    await cleanup_user_stat_keys(
        redis_client, [TEST_USER_A, TEST_USER_B], [TEST_DATE, TEST_DATE_OTHER]
    )


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


class TestGuessScript:
    @pytest.mark.asyncio
    async def test_first_wrong_guess(self, redis_repo, redis_client):
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="FAIL", guesses=1
        )

    @pytest.mark.asyncio
    async def test_consecutive_wrong_guesses(self, redis_repo, redis_client):
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="FAIL", guesses=3
        )

    @pytest.mark.asyncio
    async def test_correct_guess_after_wrongs(self, redis_repo, redis_client):
        for _ in range(3):
            await redis_repo.record_guess(
                TEST_USER_A, False, TEST_DATE, is_correct=False
            )
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=True)
        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="SUCCESS", guesses=4
        )

    @pytest.mark.asyncio
    async def test_first_guess_is_correct(self, redis_repo, redis_client):
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=True)
        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="SUCCESS", guesses=1
        )

    @pytest.mark.asyncio
    async def test_guess_ignored_after_success(self, redis_repo, redis_client):
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=True)
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=True)
        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="SUCCESS", guesses=1
        )

    @pytest.mark.asyncio
    async def test_guess_ignored_after_giveup(self, redis_repo, redis_client):
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_giveup(TEST_USER_A, False, TEST_DATE)
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=True)
        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="GIVEUP", guesses=1
        )


class TestHintScript:
    @pytest.mark.asyncio
    async def test_first_hint_no_prior_state(self, redis_repo, redis_client):
        await redis_repo.record_hint(TEST_USER_A, False, TEST_DATE)
        await assert_stat(redis_client, TEST_USER_A, TEST_DATE, status="FAIL", hints=1)

    @pytest.mark.asyncio
    async def test_consecutive_hints(self, redis_repo, redis_client):
        await redis_repo.record_hint(TEST_USER_A, False, TEST_DATE)
        await redis_repo.record_hint(TEST_USER_A, False, TEST_DATE)
        await redis_repo.record_hint(TEST_USER_A, False, TEST_DATE)
        await assert_stat(redis_client, TEST_USER_A, TEST_DATE, status="FAIL", hints=3)

    @pytest.mark.asyncio
    async def test_hint_ignored_after_success(self, redis_repo, redis_client):
        await redis_repo.record_hint(TEST_USER_A, False, TEST_DATE)
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=True)
        await redis_repo.record_hint(TEST_USER_A, False, TEST_DATE)
        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="SUCCESS", hints=1
        )

    @pytest.mark.asyncio
    async def test_hint_ignored_after_giveup(self, redis_repo, redis_client):
        await redis_repo.record_hint(TEST_USER_A, False, TEST_DATE)
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_giveup(TEST_USER_A, False, TEST_DATE)
        await redis_repo.record_hint(TEST_USER_A, False, TEST_DATE)
        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="GIVEUP", hints=1
        )


class TestGiveupScript:
    @pytest.mark.asyncio
    async def test_giveup_during_game(self, redis_repo, redis_client):
        for _ in range(3):
            await redis_repo.record_guess(
                TEST_USER_A, False, TEST_DATE, is_correct=False
            )
        await redis_repo.record_giveup(TEST_USER_A, False, TEST_DATE)
        await assert_stat(redis_client, TEST_USER_A, TEST_DATE, status="GIVEUP")

    @pytest.mark.asyncio
    async def test_giveup_as_first_action(self, redis_repo, redis_client):
        await redis_repo.record_giveup(TEST_USER_A, False, TEST_DATE)
        await assert_stat(redis_client, TEST_USER_A, TEST_DATE, status="GIVEUP")

    @pytest.mark.asyncio
    async def test_giveup_ignored_after_success(self, redis_repo, redis_client):
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=True)
        await redis_repo.record_giveup(TEST_USER_A, False, TEST_DATE)
        await assert_stat(redis_client, TEST_USER_A, TEST_DATE, status="SUCCESS")

    @pytest.mark.asyncio
    async def test_duplicate_giveup_ignored(self, redis_repo, redis_client):
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_giveup(TEST_USER_A, False, TEST_DATE)
        await redis_repo.record_giveup(TEST_USER_A, False, TEST_DATE)
        await assert_stat(redis_client, TEST_USER_A, TEST_DATE, status="GIVEUP")


class TestCompositeScenarios:
    @pytest.mark.asyncio
    async def test_normal_game_wrong_hint_correct(self, redis_repo, redis_client):
        """guess(wrong) -> hint -> guess(wrong) -> guess(correct)"""
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_hint(TEST_USER_A, False, TEST_DATE)
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=True)
        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="SUCCESS", guesses=3, hints=1
        )

    @pytest.mark.asyncio
    async def test_giveup_game(self, redis_repo, redis_client):
        """guess(wrong) -> guess(wrong) -> giveup"""
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_giveup(TEST_USER_A, False, TEST_DATE)
        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="GIVEUP", guesses=2
        )

    @pytest.mark.asyncio
    async def test_actions_ignored_after_giveup(self, redis_repo, redis_client):
        """guess(wrong) -> giveup -> guess(correct) -> hint — all ignored after giveup"""
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_giveup(TEST_USER_A, False, TEST_DATE)
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=True)
        await redis_repo.record_hint(TEST_USER_A, False, TEST_DATE)
        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="GIVEUP", guesses=1
        )


class TestStatIsolation:
    @pytest.mark.asyncio
    async def test_different_users_isolated(self, redis_repo, redis_client):
        """Two users on the same date get independent stat hashes."""
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_guess(TEST_USER_B, False, TEST_DATE, is_correct=True)

        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="FAIL", guesses=1
        )
        await assert_stat(
            redis_client, TEST_USER_B, TEST_DATE, status="SUCCESS", guesses=1
        )

    @pytest.mark.asyncio
    async def test_different_dates_isolated(self, redis_repo, redis_client):
        """Same user on different dates gets independent stat hashes."""
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=False)
        await redis_repo.record_guess(
            TEST_USER_A, False, TEST_DATE_OTHER, is_correct=True
        )

        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="FAIL", guesses=1
        )
        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE_OTHER, status="SUCCESS", guesses=1
        )


class TestGuestKeyRouting:
    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self, redis_client):
        await cleanup_user_stat_keys(redis_client, [TEST_USER_A], [TEST_DATE])
        await cleanup_guest_stat_keys(redis_client, [TEST_GUEST_A], [TEST_DATE])
        yield
        await cleanup_user_stat_keys(redis_client, [TEST_USER_A], [TEST_DATE])
        await cleanup_guest_stat_keys(redis_client, [TEST_GUEST_A], [TEST_DATE])

    @pytest.mark.asyncio
    async def test_guest_record_writes_to_guest_key(self, redis_repo, redis_client):
        """is_guest=True should write to guest:* key, not user:* key."""
        await redis_repo.record_guess(TEST_GUEST_A, True, TEST_DATE, is_correct=True)

        guest_key = RedisStatKeys.from_guest_and_date(TEST_GUEST_A, TEST_DATE).key
        user_key = RedisStatKeys.from_user_and_date(TEST_GUEST_A, TEST_DATE).key

        assert await redis_client.exists(guest_key) == 1
        assert await redis_client.exists(user_key) == 0

    @pytest.mark.asyncio
    async def test_same_uuid_user_and_guest_are_isolated(
        self, redis_repo, redis_client
    ):
        """Same UUID used as user and guest must not interfere."""
        await redis_repo.record_guess(TEST_USER_A, False, TEST_DATE, is_correct=True)
        await redis_repo.record_guess(TEST_USER_A, True, TEST_DATE, is_correct=False)

        user_data = await redis_client.hgetall(
            RedisStatKeys.from_user_and_date(TEST_USER_A, TEST_DATE).key
        )
        guest_data = await redis_client.hgetall(
            RedisStatKeys.from_guest_and_date(TEST_USER_A, TEST_DATE).key
        )

        assert user_data.get("status") == "SUCCESS"
        assert guest_data.get("status") == "FAIL"
