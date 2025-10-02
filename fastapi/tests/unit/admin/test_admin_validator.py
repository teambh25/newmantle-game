import datetime

import pytest

import app.exceptions as exc
from app.features.admin.validator import Validator


@pytest.fixture
def key_num():
    return 3


@pytest.fixture
def mock_validator(today, max_rank):
    return Validator(today=today, max_rank=max_rank)


def test_validate_quiz_success(mock_validator, quiz_factory):
    """
    Should not raise when quiz is valid.
    """
    valid_quiz = quiz_factory()
    mock_validator.validate_quiz(valid_quiz)  # no raises


def test_validate_quiz_raises_with_before_today(mock_validator, quiz_factory, today):
    """
    Should raise if quiz date is before today.
    """
    past = today - datetime.timedelta(days=1)
    invalid_quiz = quiz_factory(date=past)

    with pytest.raises(
        exc.QuizValidationError, match="Quiz date cannot be before today"
    ):
        mock_validator.validate_quiz(invalid_quiz)


def test_validate_quiz_raises_when_answer_not_hangul(mock_validator, quiz_factory):
    """
    Should raise if the answer is not Hangul.
    """
    invalid_quiz = quiz_factory(answer={"word": "Answer"})  # Use a non-Hangul answer

    with pytest.raises(exc.QuizValidationError, match="Answer is not hangul"):
        mock_validator.validate_quiz(invalid_quiz)


def test_validate_quiz_raises_when_answer_in_scores(mock_validator, quiz_factory):
    """
    Should raise if the answer appears in scores.
    """
    invalid_quiz = quiz_factory(
        answer={"word": "정답"},
        scores={"정답": 100, "사과": 95, "배": 90, "바나나": 85},
    )

    with pytest.raises(exc.QuizValidationError, match="Answer is included in scores"):
        mock_validator.validate_quiz(invalid_quiz)


def test_validate_quiz_raises_when_scores_too_short(mock_validator, quiz_factory):
    """
    Should raise if scores are fewer than max_rank.
    """
    invalid_quiz = quiz_factory(scores={"사과": 95, "배": 90})  # provide only 2 scores

    with pytest.raises(
        exc.QuizValidationError, match="The length of scores is less than max rank"
    ):
        mock_validator.validate_quiz(invalid_quiz)


def test_validate_quiz_raises_when_scores_include_non_hangul(
    mock_validator, quiz_factory
):
    """
    Should raise if scores include non-Hangul words.
    """
    invalid_quiz = quiz_factory(
        scores={"apple": 95, "pear": 90, "banana": 85}
    )  # Use a non-Hangul word in scores
    with pytest.raises(
        exc.QuizValidationError, match="The scores includes non-hangul word"
    ):
        mock_validator.validate_quiz(invalid_quiz)


@pytest.mark.parametrize("date_fixture", ["yesterday", "tomorrow"])
def test_validate_delete_date_success_with_non_today(
    mock_validator, request, date_fixture
):
    """
    Should not raise when deleting quizzes from non-today dates.
    """
    date = request.getfixturevalue(date_fixture)
    mock_validator.validate_delete_date(date)


def test_validate_delete_date_raises_with_today(mock_validator, today):
    """
    Should raise if trying to delete today's quiz.
    """
    with pytest.raises(exc.DateNotAllowed, match="Can't delete today's quiz"):
        mock_validator.validate_delete_date(today)


def test_validate_deleted_cnt_success(mock_validator, key_num):
    """
    Should not raise when all keys are deleted.
    """
    deleted_cnt = key_num  # deleted all keys

    mock_validator.validate_deleted_cnt(deleted_cnt, key_num)  # no exception


def test_validate_deleted_cnt_raises_when_none_deleted(mock_validator, key_num):
    """
    Should raise when no keys were deleted.
    """
    deleted_cnt = 0  # none deleted

    with pytest.raises(exc.QuizNotFound, match="Quiz data not found"):
        mock_validator.validate_deleted_cnt(deleted_cnt, key_num)


def test_validate_deleted_cnt_raises_when_incomplete(mock_validator, key_num):
    """
    Should raise when only some keys are deleted.
    """
    deleted_cnt = key_num - 1  # incomplete

    with pytest.raises(
        exc.QuizInconsistentError,
        match=f"Inconsistent quiz data detected, only {deleted_cnt} keys were found and deleted",
    ):
        mock_validator.validate_deleted_cnt(deleted_cnt, key_num)
