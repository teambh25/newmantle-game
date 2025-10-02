import datetime

import app.exceptions as exc
import app.schemas as schemas
from app.cores.redis import ANSWER_INDICATOR, DELIMITER, RedisKeys
from app.features.game.repository import GameRepo


class GameServiceV2:
    def __init__(self, game_repo: GameRepo, today: datetime.date):
        self.repo = game_repo
        self.today = today

    async def guess(self, date: datetime.date, word: str):
        scores_key = RedisKeys.from_date(date).scores_key
        score_rank = await self.repo.fetch_score_rank_by_word(scores_key, word)
        if score_rank is None:
            raise exc.WordNotFound(f"date={date}, word={word}")
        if score_rank == ANSWER_INDICATOR:
            answer = await self._get_answer(date)
            resp = {"correct": True, "score": None, "rank": None, "answer": answer}
        else:
            score, rank = self._extract_score_and_rank(score_rank)
            resp = {"correct": False, "score": score, "rank": rank, "answer": None}
        return resp

    async def hint(self, date: datetime.date, rank: int):
        ranking_key = RedisKeys.from_date(date).ranking_key
        word_score = await self.repo.fetch_word_score_by_rank(ranking_key, rank)
        if word_score is None:
            raise exc.RankNotFound(f"date={date}, rank={rank}")
        if rank == 0:
            initial_consonant = word_score
            resp = {"hint": initial_consonant, "score": None}
        else:
            word, score = self._extract_word_and_score(word_score)
            resp = {"hint": word, "score": score}
        return resp

    async def give_up(self, date: datetime.date):
        if self._is_future_date(date):
            raise exc.DateNotAllowed(f"date={date}")
        answer = await self._get_answer(date)
        return answer

    def _is_future_date(self, date: datetime.date):
        return date > self.today

    async def _get_answer(self, date: datetime.date):
        answer_key = RedisKeys.from_date(date).answers_key
        answer = await self.repo.fetch_answer_by_date(answer_key)
        if answer is None:
            raise exc.QuizNotFound("answer not found")
        return schemas.Answer.model_validate_json(answer)

    @staticmethod
    def _extract_score_and_rank(score_rank: str):
        score, rank = score_rank.split(DELIMITER)
        return float(score), int(rank)

    @staticmethod
    def _extract_word_and_score(word_score: str):
        word, score = word_score.split(DELIMITER)
        return word, float(score)
