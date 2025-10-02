import app.schemas as schemas
import app.utils as utils
from app.cores.redis import ANSWER_INDICATOR, DELIMITER, RedisKeys, RedisQuizData


class QuizBuilder:
    def __init__(self, max_rank: int):
        self.max_rank = max_rank

    def build_redis_quiz(self, quiz: schemas.Quiz):
        scores_map, ranking_map = self._get_scores_ranking_maps(quiz)
        ans_json_str = quiz.answer.model_dump_json()
        expire_datetime = utils.get_day_after_tomorrow_1am(quiz.date)
        redis_keys = RedisKeys.from_date(quiz.date)
        return RedisQuizData(
            keys=redis_keys,
            answer=ans_json_str,
            scores_map=scores_map,
            ranking_map=ranking_map,
            expire_at=expire_datetime,
        )

    def _get_scores_ranking_maps(self, quiz: schemas.Quiz):
        sorted_scores = sorted(quiz.scores.items(), key=lambda x: x[1], reverse=True)
        scores_map = {
            word: f"{score:.2f}{DELIMITER}{self._clamp_rank(rank)}"
            for rank, (word, score) in enumerate(sorted_scores, start=1)
        }
        scores_map[quiz.answer.word] = ANSWER_INDICATOR
        ranking_map = {
            rank: f"{word}{DELIMITER}{score:.2f}"
            for rank, (word, score) in enumerate(
                sorted_scores[: self.max_rank], start=1
            )
        }
        ranking_map[0] = utils.extract_initial_consonant(
            quiz.answer.word
        )  # consoant hint for answer
        return scores_map, ranking_map

    def _clamp_rank(self, rank: int):
        return rank if rank <= self.max_rank else -1
