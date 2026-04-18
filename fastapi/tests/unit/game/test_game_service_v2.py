import datetime

import pytest

import app.exceptions as exc
import app.schemas as schemas
from app.features.common.redis_keys import ANSWER_INDICATOR, RedisQuizKeys
from app.features.game.repository import GameRepo
from app.features.game.v2.service import GameServiceV2


@pytest.fixture
def today():
    return datetime.date(2025, 8, 29)


@pytest.fixture
def mock_game_repo(mocker):
    return mocker.MagicMock(spec=GameRepo)


@pytest.fixture
def mock_answer():
    return schemas.Answer(word="정답", tag="정답 태그", description="정답 설명입니다.")


@pytest.fixture
def game_service(mock_game_repo, today):
    return GameServiceV2(mock_game_repo, today)


class TestGuess:
    @pytest.mark.asyncio
    async def test_success_with_answer(
        self, game_service, mock_game_repo, mock_answer, today
    ):
        """Test the 'guess' method for a answer word."""
        mock_game_repo.fetch_key_exists_and_score_rank.return_value = (
            True,
            ANSWER_INDICATOR,
        )
        mock_game_repo.fetch_answer_by_date.return_value = mock_answer.model_dump_json()

        correct, score, rank, answer = await game_service.guess(today, mock_answer.word)
        assert (correct, score, rank, answer) == (True, None, None, mock_answer)

    @pytest.mark.asyncio
    async def test_success_with_non_answer(self, game_service, mock_game_repo, today):
        """Test the 'guess' method for a non-answer word."""
        mock_game_repo.fetch_key_exists_and_score_rank.return_value = (True, "95.5|120")

        correct, score, rank, answer = await game_service.guess(today, "단어")
        assert (correct, score, rank, answer) == (False, 95.5, 120, None)

    @pytest.mark.parametrize("days", [1, 2, 3])
    @pytest.mark.asyncio
    async def test_raises_when_date_not_allowed_future(self, game_service, today, days):
        """Test the 'guess' method for future dates."""
        date = today + datetime.timedelta(days=days)
        with pytest.raises(exc.DateNotAllowed):
            await game_service.guess(date, "단어")

    @pytest.mark.asyncio
    async def test_raises_when_date_not_allowed_too_old(self, game_service, today):
        """Test the 'guess' method for dates beyond the TTL window."""
        date = today - datetime.timedelta(days=RedisQuizKeys.TTL_DAYS)
        with pytest.raises(exc.DateNotAllowed):
            await game_service.guess(date, "단어")

    @pytest.mark.asyncio
    async def test_raises_when_word_not_found(
        self, game_service, mock_game_repo, today
    ):
        """Test the 'guess' method when word doesn't exist in a valid quiz."""
        mock_game_repo.fetch_key_exists_and_score_rank.return_value = (True, None)

        with pytest.raises(exc.WordNotFound):
            await game_service.guess(today, "없는 단어")

    @pytest.mark.asyncio
    async def test_raises_when_quiz_not_found(
        self, game_service, mock_game_repo, today
    ):
        """Test the 'guess' method when quiz data is missing for a valid date."""
        mock_game_repo.fetch_key_exists_and_score_rank.return_value = (False, None)

        with pytest.raises(RuntimeError):
            await game_service.guess(today, "단어")


class TestHint:
    @pytest.mark.asyncio
    async def test_success_with_answer(self, game_service, mock_game_repo, today):
        """Test the 'hint' method for answer (rank 0), returns initial consonant."""
        initial_consonant = "ㅈㄷ"
        mock_game_repo.fetch_word_score.return_value = initial_consonant

        hint_word, score = await game_service.hint(today, 0)
        assert (hint_word, score) == (initial_consonant, None)

    @pytest.mark.asyncio
    async def test_success_with_non_answer(self, game_service, mock_game_repo, today):
        """Test the 'hint' method for a non-answer rank, returns word and score."""
        mock_game_repo.fetch_word_score.return_value = "사과|98.7"

        hint_word, score = await game_service.hint(today, 10)
        assert (hint_word, score) == ("사과", 98.7)

    @pytest.mark.parametrize("days", [1, 2, 3])
    @pytest.mark.asyncio
    async def test_raises_when_date_not_allowed_future(self, game_service, today, days):
        """Test the 'hint' method for future dates."""
        date = today + datetime.timedelta(days=days)
        with pytest.raises(exc.DateNotAllowed):
            await game_service.hint(date, 1)

    @pytest.mark.asyncio
    async def test_raises_when_date_not_allowed_too_old(self, game_service, today):
        """Test the 'hint' method for dates beyond the TTL window."""
        date = today - datetime.timedelta(days=RedisQuizKeys.TTL_DAYS)
        with pytest.raises(exc.DateNotAllowed):
            await game_service.hint(date, 1)

    @pytest.mark.asyncio
    async def test_raises_when_quiz_not_found(
        self, game_service, mock_game_repo, today
    ):
        """Test the 'hint' method when rank data is missing — treated as a data integrity issue."""
        # rank is validated by the router, so None here means server-side data is missing.
        mock_game_repo.fetch_word_score.return_value = None

        with pytest.raises(RuntimeError):
            await game_service.hint(today, 1)


class TestGiveUp:
    @pytest.mark.asyncio
    async def test_success_with_valid_date(
        self, game_service, mock_game_repo, mock_answer, today
    ):
        """Test the 'give_up' method for a valid date."""
        mock_game_repo.fetch_answer_by_date.return_value = mock_answer.model_dump_json()

        result = await game_service.give_up(today)
        assert result == mock_answer

    @pytest.mark.parametrize("days", [1, 2, 3])
    @pytest.mark.asyncio
    async def test_raises_when_date_not_allowed_future(self, game_service, today, days):
        """Test the 'give_up' method for future dates."""
        date = today + datetime.timedelta(days=days)
        with pytest.raises(exc.DateNotAllowed):
            await game_service.give_up(date)

    @pytest.mark.asyncio
    async def test_raises_when_date_not_allowed_too_old(self, game_service, today):
        """Test the 'give_up' method for dates beyond the TTL window."""
        date = today - datetime.timedelta(days=RedisQuizKeys.TTL_DAYS)
        with pytest.raises(exc.DateNotAllowed):
            await game_service.give_up(date)

    @pytest.mark.asyncio
    async def test_raises_when_quiz_not_found(
        self, game_service, mock_game_repo, today
    ):
        """Test the 'give_up' method when quiz data is missing for a valid date."""
        mock_game_repo.fetch_answer_by_date.return_value = None
        with pytest.raises(RuntimeError):
            await game_service.give_up(today)
