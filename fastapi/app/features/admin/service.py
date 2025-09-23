import datetime
from dataclasses import fields

from app.cores.config import Configs
from app.cores.redis import RedisKeys, ANSWER_INDICATOR
import app.features.admin.schemas as schemas
from app.features.admin.repository import AdminRepo
import app.exceptions as exceptions
import app.utils as utils


class AdminService:
    def __init__(self, admin_repo: AdminRepo, configs: Configs, today: datetime.date):
        self.repo = admin_repo
        self.configs = configs
        self.today = today
        
    async def upsert_quiz(self, quiz: schemas.Quiz):
        self._validate_quiz(quiz)
        rd_quiz_data = self._build_redis_quiz_data(quiz)
        await self.repo.upsert_quiz(rd_quiz_data)
    
    async def read_all_answers(self):
        answer_keys, answer_words = await self.repo.fetch_all_answers()
        return {
            RedisKeys.extract_date_from_key(answer_key): answer_word
            for answer_key, answer_word in zip(answer_keys, answer_words)
        }
    
    async def delete_quiz(self, date: datetime.date):
        self._validate_delete_date(date)
        redis_keys = RedisKeys.from_date(date)
        deleted_cnt = await self.repo.delete_quiz(redis_keys)
        self._validate_deleted_cnt(deleted_cnt, redis_keys)

    def _build_redis_quiz_data(self, quiz: schemas.Quiz):
        scores_map, ranking_map = self._get_scores_ranking_maps(quiz)
        expire_datetime = utils.get_day_after_tomorrow_1am(quiz.date)
        redis_keys = RedisKeys.from_date(quiz.date)
        return schemas.RedisQuizData(
            keys=redis_keys,
            answer_word=quiz.answer,
            scores_map=scores_map,
            ranking_map=ranking_map,
            expire_at=expire_datetime,
        )
    
    def _validate_quiz(self, quiz: schemas.Quiz):
        if quiz.date < self.today:
            raise exceptions.InvalidParameter("Quiz date cannot be before today")
        if not utils.is_hangul_string(quiz.answer):
            raise exceptions.InvalidParameter("Answer is not hangul")
        if quiz.answer in quiz.scores:
            raise exceptions.InvalidParameter("Answer is included in scores")
        if len(quiz.scores) < self.configs.max_rank:
            raise exceptions.InvalidParameter("The length of scores is less than max rank")        
        if not all(utils.is_hangul_string(word) for word in quiz.scores):
            raise exceptions.InvalidParameter("The scores includes non-hangul word")
    
    def _validate_delete_date(self, date: datetime.date):
        if date == self.today:
            raise exceptions.InvalidParameter("Can't delete today's quiz")

    def _validate_deleted_cnt(self, deleted_cnt: int, redis_keys: RedisKeys):
        if deleted_cnt == 0:
            raise exceptions.QuizNotFound("Quiz data not found for date")
        elif deleted_cnt != len(fields(redis_keys)):
            raise exceptions.InconsistentQuizData("Inconsistent quiz data detected, only {deleted_cnt} keys were found and deleted")
        
    def _get_scores_ranking_maps(self, quiz: schemas.Quiz):
        sorted_scores = sorted(quiz.scores.items(), key=lambda x: x[1], reverse=True)
        scores_map = {word: f"{score:.2f}|{self._clamp_rank(rank)}" for rank, (word, score) in enumerate(sorted_scores, start=1)}
        scores_map[quiz.answer] = ANSWER_INDICATOR
        ranking_map = {rank: f"{word}|{score:.2f}" for rank, (word, score) in enumerate(sorted_scores[:self.configs.max_rank], start=1)}
        ranking_map[0] = utils.extract_initial_consonant(quiz.answer)
        return scores_map, ranking_map
    
    def _clamp_rank(self, rank: int):
        return rank if rank <= self.configs.max_rank else -1