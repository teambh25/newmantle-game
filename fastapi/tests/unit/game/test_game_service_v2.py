import datetime

import pytest

import app.exceptions as exc
import app.schemas as schemas
from app.cores.redis import ANSWER_INDICATOR
from app.features.game.repository import GameRepo
from app.features.game.v2.service import GameServiceV2


@pytest.fixture
def today():
    return datetime.date(2025, 8, 29)


@pytest.fixture
def mock_game_repo(mocker):
    mock_game_repo = mocker.MagicMock(spec=GameRepo)
    return mock_game_repo


@pytest.fixture
def mock_answer():
    return schemas.Answer(word="정답", tag="정답 태그", description="정답 설명입니다.")


@pytest.fixture
def game_service(mock_game_repo, today):
    return GameServiceV2(mock_game_repo, today)


@pytest.mark.asyncio
async def test_guess_sucess_with_answer(
    game_service, mock_game_repo, mock_answer, today
):
    """
    Test the 'guess' method for a answer word.
    """
    mock_game_repo.fetch_score_rank_by_word.return_value = ANSWER_INDICATOR
    mock_game_repo.fetch_answer_by_date.return_value = mock_answer.model_dump_json()

    result = await game_service.guess(today, mock_answer.word)
    assert result == {
        "correct": True,
        "score": None,
        "rank": None,
        "answer": mock_answer,
    }


@pytest.mark.asyncio
async def test_guess_sucess_with_non_answer(game_service, mock_game_repo, today):
    """
    Test the 'guess' method for a non answer word.
    """
    non_answer = "단어"
    mock_score_rank = "95.5|120"  # score|rank
    mock_game_repo.fetch_score_rank_by_word.return_value = mock_score_rank

    result = await game_service.guess(today, non_answer)

    assert result == {"correct": False, "score": 95.5, "rank": 120, "answer": None}


@pytest.mark.asyncio
async def test_guess_raises_when_word_not_found(game_service, mock_game_repo, today):
    """
    Test the 'guess' method when can't find word (repo returns None).
    """
    invalid_word = "없는 단어"
    mock_game_repo.fetch_score_rank_by_word.return_value = None

    with pytest.raises(exc.WordNotFound):
        await game_service.guess(today, invalid_word)


@pytest.mark.asyncio
async def test_hint_success_with_answer(game_service, mock_game_repo, today):
    """
    Test the 'hint' method for answer(=rank 0), which should return the initial consonant.
    """
    answer_rank = 0
    initial_consonant = "ㅈㄷ"  # 정답 단어 : 정답
    mock_game_repo.fetch_word_score_by_rank.return_value = initial_consonant

    result = await game_service.hint(today, answer_rank)

    assert result == {"hint": initial_consonant, "score": None}


@pytest.mark.asyncio
async def test_hint_success_with_non_answer(game_service, mock_game_repo, today):
    """
    Test the 'hint' method for a non answer(rank > 0), which should return a word and score.
    """
    mock_rank = 10
    word_score = "사과|98.7"  # word|score
    mock_game_repo.fetch_word_score_by_rank.return_value = word_score

    result = await game_service.hint(today, mock_rank)

    assert result == {"hint": "사과", "score": 98.7}


@pytest.mark.asyncio
async def test_hint_raises_with_when_rank_not_found(
    game_service, mock_game_repo, today
):
    """
    Test the 'hint' method for a rank that does not exist in the repo.
    """
    invalid_rank = -1
    mock_game_repo.fetch_word_score_by_rank.return_value = None

    with pytest.raises(exc.RankNotFound):
        await game_service.hint(today, invalid_rank)


@pytest.mark.parametrize(
    "days",
    (
        0,  # today
        1,  # yesterday
        2,
        3,
    ),
)
@pytest.mark.asyncio
async def test_give_up_sucess_with_non_future_date(
    game_service, mock_game_repo, mock_answer, today, days
):
    """
    Test the 'give up' method for a date that is today.
    """
    date = today - datetime.timedelta(days=days)
    mock_game_repo.fetch_answer_by_date.return_value = mock_answer.model_dump_json()

    result = await game_service.give_up(date)

    assert result == mock_answer


@pytest.mark.parametrize(
    "days",
    (
        1,  # tomorrow
        2,
        3,
    ),
)
@pytest.mark.asyncio
async def test_give_up_raises_with_future_date(game_service, today, days):
    """
    Test the 'give up' method for a date that is after today.
    """
    date = today + datetime.timedelta(days=days)
    with pytest.raises(exc.DateNotAllowed):
        await game_service.give_up(date)


@pytest.mark.asyncio
async def test_give_up_raises_when_quiz_not_found(game_service, mock_game_repo):
    """
    Test the 'give up' method for a date that doesn't exist answer.
    """
    no_quiz_date = datetime.date(2000, 1, 30)
    mock_game_repo.fetch_answer_by_date.return_value = None
    with pytest.raises(exc.QuizNotFound):
        await game_service.give_up(no_quiz_date)
