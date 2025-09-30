import datetime

import pytest

import app.features.admin.schemas as schemas


@pytest.fixture
def today():
    return datetime.date(2025, 8, 29)


@pytest.fixture
def tomorrow(today):
    return today + datetime.timedelta(days=1)


@pytest.fixture
def yesterday(today):
    return today - datetime.timedelta(days=1)


@pytest.fixture
def max_rank():
    return 3


@pytest.fixture
def quiz_factory(tomorrow):
    def _create_quiz(**kwargs):
        """
        Create a valid quiz with default values
        """

        # set default value
        answer = "정답"
        korean_words = ["사과", "배", "바나나"]
        scores = {word: 100.0 - 5.0 * i for i, word in enumerate(korean_words, start=1)}
        quiz_data = {
            "date": tomorrow,
            "answer": answer,
            "scores": scores,
        }

        # override
        quiz_data.update(kwargs)
        return schemas.Quiz(**quiz_data)

    return _create_quiz
