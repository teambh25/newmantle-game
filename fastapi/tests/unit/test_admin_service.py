import datetime

import pytest

from app.cores.config import Configs
from app.cores.redis import ANSWER_INDICATOR
import app.exceptions as exceptions
from app.features.admin.service import AdminService
import app.features.admin.schemas as schemas
from app.features.admin.repository import AdminRepo

TODAY = datetime.date(2025, 8, 29)
TOMORROW = datetime.date(2025, 8, 30)


@pytest.fixture
def mock_admin_repo(mocker):
    repo = mocker.MagicMock(spec=AdminRepo)
    repo.upsert_quiz = mocker.AsyncMock()
    repo.fetch_all_answers = mocker.AsyncMock()
    repo.delete_quiz = mocker.AsyncMock()
    return repo


@pytest.fixture
def mock_configs(mocker):
    configs = mocker.MagicMock(spec=Configs)
    configs.max_rank = 10
    return configs


@pytest.fixture
def mock_admin_service(mock_admin_repo, mock_configs):
    return AdminService(mock_admin_repo, mock_configs, TODAY)


@pytest.fixture
def quiz_factory():
    def _create_quiz(scores_update=None, **kwargs):
        answer = "정답"
        korean_20_words = [
            "집", "학교", "책", "밥", "물", "차", "번개", "길", "손", "눈",
            "코", "입", "귀", "발", "버스", "자전거", "기차", "강", "산", "바다",
        ]
        scores = {word: 100.0 - 0.5 * i for i, word in enumerate(korean_20_words, start=1)}
        if scores_update:
            scores.update(scores_update)
        quiz_data = {
            "date": TOMORROW,
            "answer": answer,
            "scores": scores,
        }
        quiz_data.update(kwargs)
        return schemas.Quiz(**quiz_data)
    return _create_quiz


@pytest.mark.asyncio
async def test_upsert_quiz_success(mock_admin_service, mock_admin_repo, quiz_factory):
    """
    Test the successful creation and upserting of a quiz.
    """
    valid_quiz = quiz_factory()
    await mock_admin_service.upsert_quiz(valid_quiz)

    mock_admin_repo.upsert_quiz.assert_called_once()
    call_args = mock_admin_repo.upsert_quiz.call_args
    redis_data = call_args.args[0]
    assert isinstance(redis_data, schemas.RedisQuizData)
    assert redis_data.answer_word == "정답"
    assert redis_data.scores_map["정답"] == ANSWER_INDICATOR
    assert len(redis_data.scores_map) == 21    # 21 words + 1 answer
    assert redis_data.ranking_map[0] == "ㅈㄷ"  # Check initial consonant
    assert len(redis_data.ranking_map) == 11   # 1~10 ranks + rank 0(answer)
    assert redis_data.expire_at == datetime.datetime(2025, 8, 30, 16, 0, 0)  # next 1am (UTC +9)


@pytest.mark.asyncio
async def test_upsert_quiz_validation_fails_date_in_past(mock_admin_service, quiz_factory):
    """Test that upsert_quiz raises an error if the quiz date is before today."""
    past_date = TODAY - datetime.timedelta(days=1)
    invalid_quiz = quiz_factory(date=past_date)
    
    with pytest.raises(exceptions.InvalidParameter, match="Quiz date cannot be before today"):
        await mock_admin_service.upsert_quiz(invalid_quiz)


@pytest.mark.asyncio
async def test_upsert_quiz_validation_fails_answer_in_scores(mock_admin_service, quiz_factory):
    """Test that upsert_quiz raises an error if the answer is in the scores dict."""
    invalid_quiz = quiz_factory(scores_update={"정답": 100})

    with pytest.raises(exceptions.InvalidParameter, match="Answer is included in scores"):
        await mock_admin_service.upsert_quiz(invalid_quiz)


@pytest.mark.asyncio
async def test_upsert_quiz_validation_fails_not_enough_scores(mock_admin_service, quiz_factory):
    """Test that upsert_quiz raises an error if there are not enough scores."""
    invalid_quiz = quiz_factory(scores={"사과": 50, "배": 45, "바나나": 20})  # max_rank is 10, so we provide only 3 scores
    
    with pytest.raises(exceptions.InvalidParameter, match="The length of scores is less than max rank"):
        await mock_admin_service.upsert_quiz(invalid_quiz)


@pytest.mark.asyncio
async def test_upsert_quiz_fails_answer_not_hangul(mock_admin_service, quiz_factory):
    """Test error raising when the answer cannot be processed for an initial consonant hint."""    
    invalid_quiz = quiz_factory(answer="English")  # Use a non-Hangul answer
    with pytest.raises(exceptions.InvalidParameter, match="Answer is not hangul"):
        await mock_admin_service.upsert_quiz(invalid_quiz)


@pytest.mark.asyncio
async def test_upsert_quiz_fails_scores_not_hangul(mock_admin_service, quiz_factory):
    """Test error raising when the answer cannot be processed for an initial consonant hint."""    
    invalid_quiz = quiz_factory(scores_update={"word": 100})  # Use a non-Hangul word in scores
    with pytest.raises(exceptions.InvalidParameter, match="The scores includes non-hangul word"):
        await mock_admin_service.upsert_quiz(invalid_quiz)


@pytest.mark.asyncio
async def test_read_all_answers_success(mock_admin_service, mock_admin_repo):
    """Test successfully fetching and transforming all answers."""
    date1 = datetime.date(2025, 8, 20)
    date2 = datetime.date(2025, 8, 21)
    mock_keys = [f"quiz:{date1}:answers", f"quiz:{date2}:answers"]
    mock_words = ["첫번째답", "두번째답"]
    mock_admin_repo.fetch_all_answers.return_value = (mock_keys, mock_words)

    result = await mock_admin_service.read_all_answers()

    mock_admin_repo.fetch_all_answers.assert_called_once()
    expected_result = {
        date1: "첫번째답",
        date2: "두번째답"
    }
    assert result == expected_result


@pytest.mark.asyncio
async def test_delete_quiz_success(mock_admin_service, mock_admin_repo):
    """Test the successful deletion of a quiz on a future date."""
    valid_deleted_cnt = 3
    mock_admin_repo.delete_quiz.return_value = valid_deleted_cnt

    await mock_admin_service.delete_quiz(TOMORROW)

    mock_admin_repo.delete_quiz.assert_called_once()
    call_args = mock_admin_repo.delete_quiz.call_args
    redis_keys_arg = call_args.args[0]
    assert redis_keys_arg.answers_key == f"quiz:{TOMORROW}:answers"


@pytest.mark.asyncio
async def test_delete_quiz_validation_fails_delete_date_today(mock_admin_service):
    """Test that deleting today's quiz is not allowed."""
    with pytest.raises(exceptions.InvalidParameter, match="Can't delete today's quiz"):
        await mock_admin_service.delete_quiz(TODAY)


@pytest.mark.asyncio
async def test_delete_quiz_fails_invalid_date(mock_admin_service, mock_admin_repo):
    """Test that deleting today's quiz is not allowed."""
    no_quiz_date = datetime.date(2300, 1, 30)
    no_quiz_deleted_cnt = 0
    mock_admin_repo.delete_quiz.return_value = no_quiz_deleted_cnt
    with pytest.raises(exceptions.QuizNotFound, match="Quiz data not found for date"):
        await mock_admin_service.delete_quiz(no_quiz_date)


@pytest.mark.asyncio
async def test_delete_quiz_fails_inconsistent_data(mock_admin_service, mock_admin_repo):
    """Test that deleting today's quiz is not allowed."""
    date = datetime.date(2025, 9, 30)  # any date
    inconsistent_quiz_deleted_cnt = 1  # 1 or 2
    mock_admin_repo.delete_quiz.return_value = inconsistent_quiz_deleted_cnt  # not deleted all key
    with pytest.raises(exceptions.InconsistentQuizData):
        await mock_admin_service.delete_quiz(date)