import datetime

import pytest

from app.cores.redis import RedisKeys, ANSWER_INDICATOR
import app.exceptions as exceptions
from app.features.game.service import GameService
from app.features.game.repository import GameRepo


@pytest.fixture
def mock_game_repo(mocker):
    mock_game_repo = mocker.MagicMock(spec=GameRepo)
    mock_game_repo.get_score_rank_by_word = mocker.AsyncMock()
    return mock_game_repo


@pytest.fixture
def game_service(mock_game_repo):
    return GameService(mock_game_repo)


@pytest.fixture
def test_date():
    return datetime.date(2025, 8, 29)


@pytest.fixture
def expected_scores_key(test_date):
    return RedisKeys.from_date(test_date).scores_key


@pytest.fixture
def expected_ranking_key(test_date):
    return RedisKeys.from_date(test_date).ranking_key


@pytest.mark.asyncio
async def test_guess_with_correct_answer(game_service, mock_game_repo, test_date, expected_scores_key):
    """
    Test the 'guess' method for a correct answer.
    """
    correct_word = "정답"
    mock_game_repo.get_score_rank_by_word.return_value = ANSWER_INDICATOR
    
    result = await game_service.guess(test_date, correct_word)

    mock_game_repo.get_score_rank_by_word.assert_called_once_with(expected_scores_key, correct_word)
    assert result == {"correct": True, "score": None, "rank": None}


@pytest.mark.asyncio
async def test_guess_with_incorrect_answer(game_service, mock_game_repo, test_date, expected_scores_key):
    """
    Test the 'guess' method for a valid but incorrect answer.
    """
    incorrect_word = "단어"
    mock_score_rank = "95.5|120"  # score|rank
    mock_game_repo.get_score_rank_by_word.return_value = mock_score_rank

    result = await game_service.guess(test_date, incorrect_word)

    mock_game_repo.get_score_rank_by_word.assert_called_once_with(expected_scores_key, incorrect_word)
    assert result == {"correct": False, "score": 95.5, "rank": 120}


@pytest.mark.asyncio
async def test_guess_with_invalid_word(game_service, mock_game_repo, test_date, expected_scores_key):
    """
    Test the 'guess' method when the word is invalid (repo returns None).
    """
    invalid_word = "잘못된 단어"
    mock_game_repo.get_score_rank_by_word.return_value = None

    with pytest.raises(exceptions.InvalidParameter):
        await game_service.guess(test_date, invalid_word)
    mock_game_repo.get_score_rank_by_word.assert_called_once_with(expected_scores_key, invalid_word)


@pytest.mark.asyncio
async def test_hint_for_rank_zero(game_service, mock_game_repo, test_date, expected_ranking_key):
    """
    Test the 'hint' method for rank 0, which should return the initial consonant.
    """
    rank = 0
    initial_consonant = "ㅈㄷ"  # 정답 단어 : 정답
    mock_game_repo.get_word_score_by_rank.return_value = initial_consonant

    result = await game_service.hint(test_date, rank)

    mock_game_repo.get_word_score_by_rank.assert_called_once_with(expected_ranking_key, rank)
    assert result == {"hint": initial_consonant, "score": None}


@pytest.mark.asyncio
async def test_hint_for_valid_rank(game_service, mock_game_repo, test_date, expected_ranking_key):
    """
    Test the 'hint' method for a valid rank > 0, which should return a word and score.
    """
    rank = 10
    word_score_from_repo = "사과|98.7"  # word|score
    mock_game_repo.get_word_score_by_rank.return_value = word_score_from_repo

    result = await game_service.hint(test_date, rank)

    mock_game_repo.get_word_score_by_rank.assert_called_once_with(expected_ranking_key, rank)
    assert result == {"hint": "사과", "score": 98.7}


@pytest.mark.asyncio
async def test_hint_for_invalid_rank(game_service, mock_game_repo, test_date, expected_ranking_key):
    """
    Test the 'hint' method for a rank that does not exist in the repo.
    """
    invalid_rank = -1
    mock_game_repo.get_word_score_by_rank.return_value = None

    with pytest.raises(exceptions.InvalidParameter):
        await game_service.hint(test_date, invalid_rank)

    mock_game_repo.get_word_score_by_rank.assert_called_once_with(expected_ranking_key, invalid_rank)