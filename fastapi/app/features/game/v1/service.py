import datetime

import app.exceptions as exc
from app.cores.redis import ANSWER_INDICATOR, DELIMITER, RedisKeys
from app.features.game.repository import GameRepo
from app.features.game.v1.adpter import V1Adapter


class GameServiceV1:
    def __init__(self, game_repo: GameRepo, today: datetime.date):
        self.repo = game_repo
        self.today = today

    async def guess(self, date: datetime.date, word: str):
        scores_key = RedisKeys.from_date(date).scores_key
        score_rank = await self.repo.fetch_score_rank_by_word(scores_key, word)
        if score_rank is None:
            raise exc.WordNotFound(f"guess | date={date}, word={word}")
        if score_rank == ANSWER_INDICATOR:
            resp = {"correct": True, "score": None, "rank": None}
        else:
            score, rank = self._extract_score_and_rank(score_rank)
            resp = {"correct": False, "score": score, "rank": rank}
        return resp

    async def hint(self, date: datetime.date, rank: int):
        ranking_key = RedisKeys.from_date(date).ranking_key
        word_score = await self.repo.fetch_word_score_by_rank(ranking_key, rank)
        if word_score is None:
            raise exc.RankNotFound(f"hint | date={date}, rank={rank}")
        if rank == 0:
            initial_consonant = word_score
            resp = {"hint": initial_consonant, "score": None}
        else:
            word, score = self._extract_word_and_score(word_score)
            resp = {"hint": word, "score": score}
        return resp

    async def read_recent_answer(self, date: datetime.date):
        if self._is_future_date(date):
            raise exc.DateNotAllowed(f"ans | date={date}")
        answer_key = RedisKeys.from_date(date).answers_key
        answer = V1Adapter.answer_to_v1(
            await self.repo.fetch_answer_by_date(answer_key)
        )

        if answer is None:
            raise exc.QuizNotFound("ans | quiz not found")
        return answer

    def _is_future_date(self, date: datetime.date):
        return date > self.today

    @staticmethod
    def _extract_score_and_rank(score_rank: str):
        score, rank = score_rank.split(DELIMITER)
        return float(score), int(rank)

    @staticmethod
    def _extract_word_and_score(word_score: str):
        word, score = word_score.split(DELIMITER)
        return word, float(score)
