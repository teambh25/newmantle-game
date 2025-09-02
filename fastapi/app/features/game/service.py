import datetime

from app.cores.redis import RedisKeys, ANSWER_INDICATOR
from app.features.game.repository import GameRepo
import app.exceptions as exceptions


class GameService:
    def __init__(self, game_repo: GameRepo):
        self.repo = game_repo

    async def guess(self, date: datetime.date, word: str):
        scores_key = RedisKeys.from_date(date).scores_key
        score_rank = await self.repo.get_score_rank_by_word(scores_key, word)
        if score_rank is None:
            raise exceptions.InvalidParameter(f"guess | date={date}, word={word}")
        if score_rank == ANSWER_INDICATOR:
            resp = {"correct": True, "score": None, "rank": None}
        else:
            score, rank = self._extract_score_and_rank(score_rank)
            resp = {"correct": False, "score": score, "rank": rank}
        return resp
    
    async def hint(self, date: datetime.date, rank: int):
        ranking_key = RedisKeys.from_date(date).ranking_key
        word_score = await self.repo.get_word_score_by_rank(ranking_key, rank)
        if word_score is None:
            raise exceptions.InvalidParameter(f"hint | date={date}, rank={rank}")
        if rank == 0:
            initial_consonant = word_score
            resp = {"hint": initial_consonant, "score": None}
        else:
            word, score = self._extract_word_and_score(word_score)
            resp = {"hint": word, "score": score}
        return resp
    
    @staticmethod
    def _extract_score_and_rank(score_rank: str):
        score, rank = score_rank.split("|")
        return float(score), int(rank)
    
    @staticmethod
    def _extract_word_and_score(word_score: str):
        word, score = word_score.split("|")
        return word, float(score)