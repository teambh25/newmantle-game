import datetime

from app.cores.config import Configs
from app.cores.redis import RedisKeys
import app.features.admin.schemas as schemas
from app.features.admin.repository import AdminRepo
import app.exceptions as exceptions
import app.utils as utils

from loguru import logger

class AdminService:
    def __init__(self, admin_repo: AdminRepo, configs: Configs):
        self.admin_repo = admin_repo
        self.configs = configs
        
    async def upsert_quiz(self, quiz: schemas.Quiz):
        self._validate_quiz(quiz)
        rd_quiz_data = self._prepare_redis_quiz_data(quiz)
        await self.admin_repo.upsert_quiz(rd_quiz_data)
    
    async def read_all_answers(self):
        answer_keys, answer_words = await self.admin_repo.fetch_all_answers()
        return {
            RedisKeys.extract_date_from_key(answer_key): answer_word
            for answer_key, answer_word in zip(answer_keys, answer_words)
        }
    
    async def delete_quiz(self, date: datetime.date):
        self._validate_delete_date(date)
        redis_keys = RedisKeys.from_date(date)
        return await self.admin_repo.delete_quiz(redis_keys)
    
    def _validate_quiz(self, quiz: schemas.Quiz):
        today = utils.get_today_date()
        if quiz.date < today:
            raise exceptions.InvalidParameter("Quiz date cannot be before today")
        if quiz.answer in quiz.scores:
            raise exceptions.InvalidParameter(f"Answer is included in scores")
        if len(quiz.scores) < self.configs.max_rank:
            raise exceptions.InvalidParameter("The length of scores is less than max rank")
    
    def _validate_delete_date(self, date:datetime.date):
        today = utils.get_today_date()
        if date == today:
            raise exceptions.InvalidParameter("Can't delete today's quiz")

    def _prepare_redis_quiz_data(self, quiz: schemas.Quiz):
        scores_map, ranking_map = self._get_scores_ranking_maps(quiz)
        expire_datetime = self._get_expire_datetime(quiz.date)
        redis_keys = RedisKeys.from_date(quiz.date)
        return schemas.RedisQuizData(
            keys=redis_keys,
            answer_word=quiz.answer,
            scores_map=scores_map,
            ranking_map=ranking_map,
            expire_at=expire_datetime
        )

    def _get_scores_ranking_maps(self, quiz: schemas.Quiz):
        sorted_scores = sorted(quiz.scores.items(), key=lambda x:x[1], reverse=True)
        clamp_rank = lambda x : x if x<=self.configs.max_rank else -1
        scores_map = {word:f"{score:.2f}|{clamp_rank(rank)}" for rank, (word, score) in enumerate(sorted_scores, start=1)}
        scores_map[quiz.answer] = "answer"
        ranking_map = {rank:f"{word}|{score:.2f}" for rank, (word, score) in enumerate(sorted_scores[:self.configs.max_rank], start=1)}
        return scores_map, ranking_map

    def _get_expire_datetime(self, quiz_date: datetime.date):
        return datetime.datetime.combine(quiz_date, datetime.time(hour=16, minute=0, second=0)) # next day 1am(KST, UTC+9)