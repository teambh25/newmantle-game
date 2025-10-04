from typing import List, Tuple

import app.schemas as schemas
import app.utils as utils
from app.cores.redis import ANSWER_INDICATOR, RedisKeys, RedisQuizData


class QuizBuilder:
    def __init__(self, max_rank: int):
        self.max_rank = max_rank

    def build_redis_quiz(self, quiz: schemas.Quiz):
        redis_keys = RedisKeys.from_date(quiz.date)
        ans_json_str = quiz.answer.model_dump_json()
        sorted_scores = sorted(quiz.scores.items(), key=lambda x: x[1], reverse=True)
        scores_map = self._get_scores_map(sorted_scores, quiz.answer.word)
        ranking_map = self._get_ranking_map(sorted_scores, quiz.answer.word)
        expire_datetime = utils.get_day_after_tomorrow_1am(quiz.date)
        rd_quiz = RedisQuizData(
            keys=redis_keys,
            answer=ans_json_str,
            scores_map=scores_map,
            ranking_map=ranking_map,
            expire_at=expire_datetime,
        )
        return rd_quiz

    def _get_ranking_map(self, sorted_scores: List[Tuple[str, float]], ans_word: str):
        ranking_map = {
            rank: RedisQuizData.serialize_word_and_score(word, score)
            for rank, (word, score) in enumerate(
                sorted_scores[: self.max_rank], start=1
            )
        }
        ranking_map[0] = utils.extract_initial_consonant(
            ans_word
        )  # consoant hint for answer
        return ranking_map

    def _get_scores_map(self, sorted_scores: List[Tuple[str, float]], ans_word: str):
        scores_map = {
            word: RedisQuizData.serialize_score_and_rank(score, self._clamp_rank(rank))
            for rank, (word, score) in enumerate(sorted_scores, start=1)
        }
        scores_map[ans_word] = ANSWER_INDICATOR
        return scores_map

    def _clamp_rank(self, rank: int):
        return rank if rank <= self.max_rank else -1
