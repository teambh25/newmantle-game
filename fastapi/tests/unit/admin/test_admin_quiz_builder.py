import datetime

import pytest

from app.cores.redis import ANSWER_INDICATOR
from app.features.admin.quiz_builder import QuizBuilder


@pytest.fixture
def mock_quiz_builder(max_rank):
    return QuizBuilder(max_rank)


def test_build_redis_quiz(mock_quiz_builder, quiz_factory, tomorrow):
    quiz = quiz_factory()  # use default quiz

    rd_quiz = mock_quiz_builder.build_redis_quiz(quiz)

    assert (
        rd_quiz.answer == '{"word":"정답","tag":"랜덤","description":"정답입니다."}'
    )  # json string
    assert len(rd_quiz.scores_map) == 4  # 1 answer + 3 scores
    assert rd_quiz.scores_map["정답"] == ANSWER_INDICATOR
    assert rd_quiz.scores_map["사과"] == "95.00|1"
    assert rd_quiz.scores_map["배"] == "90.00|2"
    assert rd_quiz.scores_map["바나나"] == "85.00|3"
    assert len(rd_quiz.ranking_map) == 4  # 1 answer + 3 scores
    assert rd_quiz.ranking_map[0] == "ㅈㄷ"  # initial consonant hint for answer
    assert rd_quiz.ranking_map[1] == "사과|95.00"
    assert rd_quiz.ranking_map[2] == "배|90.00"
    assert rd_quiz.ranking_map[3] == "바나나|85.00"
    assert rd_quiz.expire_at == datetime.datetime.combine(
        tomorrow, datetime.time()
    ) + datetime.timedelta(days=1, hours=16)  # Expires at 1 AM, two days later
