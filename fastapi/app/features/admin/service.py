import datetime
from dataclasses import fields

import app.schemas as schemas
from app.cores.redis import RedisKeys
from app.features.admin.quiz_builder import QuizBuilder
from app.features.admin.repository import AdminRepo
from app.features.admin.validator import Validator


class AdminService:
    def __init__(
        self, admin_repo: AdminRepo, quiz_builder: QuizBuilder, validator: Validator
    ):
        self.repo = admin_repo
        self.validator = validator
        self.quiz_builder = quiz_builder

    async def upsert_quiz(self, quiz: schemas.Quiz):
        self.validator.validate_quiz(quiz)
        rd_quiz = self.quiz_builder.build_redis_quiz(quiz)
        await self.repo.upsert_quiz(rd_quiz)

    async def read_all_answers(self):
        answer_keys, answers = await self.repo.fetch_all_answers()
        return {
            RedisKeys.extract_date(key): schemas.Answer.model_validate_json(ans)
            for key, ans in zip(answer_keys, answers)
        }

    async def delete_quiz(self, date: datetime.date):
        self.validator.validate_delete_date(date)
        redis_keys = RedisKeys.from_date(date)
        deleted_cnt = await self.repo.delete_quiz(redis_keys)
        self.validator.validate_deleted_cnt(deleted_cnt, len(fields(redis_keys)))
