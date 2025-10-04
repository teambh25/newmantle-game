import datetime

import app.exceptions as exc
import app.schemas as schemas
import app.utils as utils
from app.cores.redis import ANSWER_INDICATOR, RedisKeys, RedisQuizData
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
            score, rank = RedisQuizData.deserialize_score_and_rank(score_rank)
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
            word, score = RedisQuizData.deserialize_word_and_score(word_score)
            resp = {"hint": word, "score": score}
        return resp

    async def give_up(self, date: datetime.date):
        if utils.is_future(date, self.today):
            raise exc.DateNotAllowed(f"date={date}")
        answer = await self._get_answer(date)
        return answer

    async def _get_answer(self, date: datetime.date):
        answer_key = RedisKeys.from_date(date).answers_key
        answer = await self.repo.fetch_answer_by_date(answer_key)
        if answer is None:
            raise exc.QuizNotFound("answer not found")
        return schemas.Answer.model_validate_json(answer)
