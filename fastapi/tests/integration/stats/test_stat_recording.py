"""Integration tests for stat recording via StatRepository.

Suites 1-3, 5-6 from docs/user-stats/test-plan.md.
"""

import pytest
from tests.integration.stats.conftest import (
    TEST_DATE,
    TEST_DATE_OTHER,
    TEST_USER_A,
    TEST_USER_B,
    assert_stat,
)

# ---------------------------------------------------------------------------
# Suite 1: Guess Script State Transitions
# ---------------------------------------------------------------------------


class TestGuessScript:
    @pytest.mark.asyncio
    async def test_first_wrong_guess(self, repo, redis_client, user_id, quiz_date):
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await assert_stat(redis_client, user_id, quiz_date, status="FAIL", guesses=1)

    @pytest.mark.asyncio
    async def test_consecutive_wrong_guesses(
        self, repo, redis_client, user_id, quiz_date
    ):
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await assert_stat(redis_client, user_id, quiz_date, status="FAIL", guesses=3)

    @pytest.mark.asyncio
    async def test_correct_guess_after_wrongs(
        self, repo, redis_client, user_id, quiz_date
    ):
        for _ in range(3):
            await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_guess(user_id, quiz_date, is_correct=True)
        await assert_stat(redis_client, user_id, quiz_date, status="SUCCESS", guesses=4)

    @pytest.mark.asyncio
    async def test_first_guess_is_correct(self, repo, redis_client, user_id, quiz_date):
        await repo.record_guess(user_id, quiz_date, is_correct=True)
        await assert_stat(redis_client, user_id, quiz_date, status="SUCCESS", guesses=1)

    @pytest.mark.asyncio
    async def test_guess_ignored_after_success(
        self, repo, redis_client, user_id, quiz_date
    ):
        await repo.record_guess(user_id, quiz_date, is_correct=True)
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_guess(user_id, quiz_date, is_correct=True)
        await assert_stat(redis_client, user_id, quiz_date, status="SUCCESS", guesses=1)

    @pytest.mark.asyncio
    async def test_guess_ignored_after_giveup(
        self, repo, redis_client, user_id, quiz_date
    ):
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_giveup(user_id, quiz_date)
        await repo.record_guess(user_id, quiz_date, is_correct=True)
        await assert_stat(redis_client, user_id, quiz_date, status="GIVEUP", guesses=1)


# ---------------------------------------------------------------------------
# Suite 2: Hint Script State Transitions
# ---------------------------------------------------------------------------


class TestHintScript:
    @pytest.mark.asyncio
    async def test_first_hint_no_prior_state(
        self, repo, redis_client, user_id, quiz_date
    ):
        await repo.record_hint(user_id, quiz_date)
        await assert_stat(redis_client, user_id, quiz_date, status="FAIL", hints=1)

    @pytest.mark.asyncio
    async def test_consecutive_hints(self, repo, redis_client, user_id, quiz_date):
        await repo.record_hint(user_id, quiz_date)
        await repo.record_hint(user_id, quiz_date)
        await repo.record_hint(user_id, quiz_date)
        await assert_stat(redis_client, user_id, quiz_date, status="FAIL", hints=3)

    @pytest.mark.asyncio
    async def test_hint_ignored_after_success(
        self, repo, redis_client, user_id, quiz_date
    ):
        await repo.record_hint(user_id, quiz_date)
        await repo.record_guess(user_id, quiz_date, is_correct=True)
        await repo.record_hint(user_id, quiz_date)
        await assert_stat(redis_client, user_id, quiz_date, status="SUCCESS", hints=1)

    @pytest.mark.asyncio
    async def test_hint_ignored_after_giveup(
        self, repo, redis_client, user_id, quiz_date
    ):
        await repo.record_hint(user_id, quiz_date)
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_giveup(user_id, quiz_date)
        await repo.record_hint(user_id, quiz_date)
        await assert_stat(redis_client, user_id, quiz_date, status="GIVEUP", hints=1)


# ---------------------------------------------------------------------------
# Suite 3: Giveup Script State Transitions
# ---------------------------------------------------------------------------


class TestGiveupScript:
    @pytest.mark.asyncio
    async def test_giveup_during_game(self, repo, redis_client, user_id, quiz_date):
        for _ in range(3):
            await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_giveup(user_id, quiz_date)
        await assert_stat(redis_client, user_id, quiz_date, status="GIVEUP")

    @pytest.mark.asyncio
    async def test_giveup_as_first_action(self, repo, redis_client, user_id, quiz_date):
        await repo.record_giveup(user_id, quiz_date)
        await assert_stat(redis_client, user_id, quiz_date, status="GIVEUP")

    @pytest.mark.asyncio
    async def test_giveup_ignored_after_success(
        self, repo, redis_client, user_id, quiz_date
    ):
        await repo.record_guess(user_id, quiz_date, is_correct=True)
        await repo.record_giveup(user_id, quiz_date)
        await assert_stat(redis_client, user_id, quiz_date, status="SUCCESS")

    @pytest.mark.asyncio
    async def test_duplicate_giveup_ignored(
        self, repo, redis_client, user_id, quiz_date
    ):
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_giveup(user_id, quiz_date)
        await repo.record_giveup(user_id, quiz_date)
        await assert_stat(redis_client, user_id, quiz_date, status="GIVEUP")


# ---------------------------------------------------------------------------
# Suite 5: Composite Game Flow Scenarios
# ---------------------------------------------------------------------------


class TestCompositeScenarios:
    @pytest.mark.asyncio
    async def test_normal_game_wrong_hint_correct(
        self, repo, redis_client, user_id, quiz_date
    ):
        """guess(wrong) -> hint -> guess(wrong) -> guess(correct)"""
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_hint(user_id, quiz_date)
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_guess(user_id, quiz_date, is_correct=True)
        await assert_stat(
            redis_client, user_id, quiz_date, status="SUCCESS", guesses=3, hints=1
        )

    @pytest.mark.asyncio
    async def test_giveup_game(self, repo, redis_client, user_id, quiz_date):
        """guess(wrong) -> guess(wrong) -> giveup"""
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_giveup(user_id, quiz_date)
        await assert_stat(redis_client, user_id, quiz_date, status="GIVEUP", guesses=2)

    @pytest.mark.asyncio
    async def test_actions_ignored_after_giveup(
        self, repo, redis_client, user_id, quiz_date
    ):
        """guess(wrong) -> giveup -> guess(correct) -> hint — all ignored after giveup"""
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_giveup(user_id, quiz_date)
        await repo.record_guess(user_id, quiz_date, is_correct=False)
        await repo.record_guess(user_id, quiz_date, is_correct=True)
        await repo.record_hint(user_id, quiz_date)
        await assert_stat(redis_client, user_id, quiz_date, status="GIVEUP", guesses=1)


# ---------------------------------------------------------------------------
# Suite 6: Redis Key Pattern & Isolation
# ---------------------------------------------------------------------------


class TestStatIsolation:
    @pytest.mark.asyncio
    async def test_different_users_isolated(self, repo, redis_client):
        """Two users on the same date get independent stat hashes."""
        await repo.record_guess(TEST_USER_A, TEST_DATE, is_correct=False)
        await repo.record_guess(TEST_USER_B, TEST_DATE, is_correct=True)

        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="FAIL", guesses=1
        )
        await assert_stat(
            redis_client, TEST_USER_B, TEST_DATE, status="SUCCESS", guesses=1
        )

    @pytest.mark.asyncio
    async def test_different_dates_isolated(self, repo, redis_client):
        """Same user on different dates gets independent stat hashes."""
        await repo.record_guess(TEST_USER_A, TEST_DATE, is_correct=False)
        await repo.record_guess(TEST_USER_A, TEST_DATE_OTHER, is_correct=True)

        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE, status="FAIL", guesses=1
        )
        await assert_stat(
            redis_client, TEST_USER_A, TEST_DATE_OTHER, status="SUCCESS", guesses=1
        )
