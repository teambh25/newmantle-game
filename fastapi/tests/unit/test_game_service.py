import datetime

import pytest

import app.exceptions as exceptions
from app.cores.redis import ANSWER_INDICATOR, RedisKeys
from app.features.game.repository import GameRepo
from app.features.game.service import GameService

TODAY = datetime.date(2025, 8, 29)


@pytest.fixture
def mock_game_repo(mocker):
    mock_game_repo = mocker.MagicMock(spec=GameRepo)
    return mock_game_repo


@pytest.fixture
def game_service(mock_game_repo):
    return GameService(mock_game_repo, TODAY)


@pytest.fixture
def test_date():
    return datetime.date(2025, 8, 29)


@pytest.fixture
def expected_answers_key(test_date):
    return RedisKeys.from_date(test_date).answers_key


@pytest.fixture
def expected_scores_key(test_date):
    return RedisKeys.from_date(test_date).scores_key


@pytest.fixture
def expected_ranking_key(test_date):
    return RedisKeys.from_date(test_date).ranking_key


@pytest.mark.asyncio
async def test_guess_sucess_with_answer(
    game_service, mock_game_repo, test_date, expected_scores_key
):
    """
    Test the 'guess' method for a answer word.
    """
    answer = "정답"
    mock_game_repo.fetch_score_rank_by_word.return_value = ANSWER_INDICATOR

    result = await game_service.guess(test_date, answer)

    mock_game_repo.fetch_score_rank_by_word.assert_called_once_with(
        expected_scores_key, answer
    )
    assert result == {"correct": True, "score": None, "rank": None}


@pytest.mark.asyncio
async def test_guess_sucess_with_non_answer(
    game_service, mock_game_repo, test_date, expected_scores_key
):
    """
    Test the 'guess' method for a non answer word.
    """
    non_answer = "단어"
    mock_score_rank = "95.5|120"  # score|rank
    mock_game_repo.fetch_score_rank_by_word.return_value = mock_score_rank

    result = await game_service.guess(test_date, non_answer)

    mock_game_repo.fetch_score_rank_by_word.assert_called_once_with(
        expected_scores_key, non_answer
    )
    assert result == {"correct": False, "score": 95.5, "rank": 120}


@pytest.mark.asyncio
async def test_guess_raises_with_invalid_word(
    game_service, mock_game_repo, test_date, expected_scores_key
):
    """
    Test the 'guess' method when the word is invalid (repo returns None).
    """
    invalid_word = "잘못된 단어"
    mock_game_repo.fetch_score_rank_by_word.return_value = None

    with pytest.raises(exceptions.InvalidParameter):
        await game_service.guess(test_date, invalid_word)
    mock_game_repo.fetch_score_rank_by_word.assert_called_once_with(
        expected_scores_key, invalid_word
    )


@pytest.mark.asyncio
async def test_hint_return_initial_consonant(
    game_service, mock_game_repo, test_date, expected_ranking_key
):
    """
    Test the 'hint' method for rank 0, which should return the initial consonant.
    """
    rank = 0
    initial_consonant = "ㅈㄷ"  # 정답 단어 : 정답
    mock_game_repo.fetch_word_score_by_rank.return_value = initial_consonant

    result = await game_service.hint(test_date, rank)

    mock_game_repo.fetch_word_score_by_rank.assert_called_once_with(
        expected_ranking_key, rank
    )
    assert result == {"hint": initial_consonant, "score": None}


@pytest.mark.asyncio
async def test_hint_return_word(
    game_service, mock_game_repo, test_date, expected_ranking_key
):
    """
    Test the 'hint' method for a valid rank > 0, which should return a word and score.
    """
    rank = 10
    word_score_from_repo = "사과|98.7"  # word|score
    mock_game_repo.fetch_word_score_by_rank.return_value = word_score_from_repo

    result = await game_service.hint(test_date, rank)

    mock_game_repo.fetch_word_score_by_rank.assert_called_once_with(
        expected_ranking_key, rank
    )
    assert result == {"hint": "사과", "score": 98.7}


@pytest.mark.asyncio
async def test_hint_raises_with_invalid_rank(
    game_service, mock_game_repo, test_date, expected_ranking_key
):
    """
    Test the 'hint' method for a rank that does not exist in the repo.
    """
    invalid_rank = -1
    mock_game_repo.fetch_word_score_by_rank.return_value = None

    with pytest.raises(exceptions.InvalidParameter):
        await game_service.hint(test_date, invalid_rank)

    mock_game_repo.fetch_word_score_by_rank.assert_called_once_with(
        expected_ranking_key, invalid_rank
    )


@pytest.mark.asyncio
async def test_read_recent_answer_sucess_with_today(
    game_service, mock_game_repo, expected_answers_key
):
    """
    Test the 'read_recent' method for a date that is today.
    """
    ANSWER = "정답"
    mock_game_repo.fetch_answer_by_date.return_value = ANSWER

    result = await game_service.read_recent_answer(TODAY)

    mock_game_repo.fetch_answer_by_date.assert_called_once_with(expected_answers_key)
    assert result == ANSWER


@pytest.mark.asyncio
async def test_read_recent_answer_raises_with_future_date(game_service):
    """
    Test the 'read_recent' method for a date that is after today.
    """
    future_date = TODAY + datetime.timedelta(days=1)
    with pytest.raises(exceptions.InvalidParameter):
        await game_service.read_recent_answer(future_date)


@pytest.mark.asyncio
async def test_read_recent_answer_raises_if_no_answer(game_service, mock_game_repo):
    """
    Test the 'read_recent' method for a date that doesn't exist answer.
    """
    no_ans_date = datetime.date(2000, 1, 30)
    mock_game_repo.fetch_answer_by_date.return_value = None
    with pytest.raises(exceptions.QuizNotFound):
        await game_service.read_recent_answer(no_ans_date)
