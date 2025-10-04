import datetime

import pytest

import app.schemas as schemas


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
def quiz_factory(tomorrow):
    def _create_quiz(**kwargs):
        """
        Create a valid quiz with default values
        """

        # set default value
        answer = {"word": "정답", "tag": "랜덤", "description": "정답입니다."}
        korean_words = ["사과", "배", "바나나"]
        scores = {word: 100.0 - 5.0 * i for i, word in enumerate(korean_words, start=1)}
        quiz_data = {
            "date": tomorrow,
            "answer": answer,
            "scores": scores,
        }

        # override
        if "answer" in kwargs:
            quiz_data["answer"].update(kwargs["answer"])
            del kwargs["answer"]
        quiz_data.update(kwargs)
        quiz_data["answer"] = schemas.Answer(
            **quiz_data["answer"]
        )  # answer should dict
        return schemas.Quiz(**quiz_data)

    return _create_quiz
