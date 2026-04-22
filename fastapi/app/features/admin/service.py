import datetime
import time
from dataclasses import fields
from loguru import logger

import app.exceptions as exc
import app.schemas as schemas
from app.features.admin.quiz_builder import QuizBuilder
from app.features.admin.repository import AdminRepo
from app.features.admin.validator import Validator
from app.features.common.redis_keys import RedisQuizKeys
from app.features.common.repository import OutageDateRepository


class AdminService:
    def __init__(
        self,
        admin_repo: AdminRepo,
        outage_repo: OutageDateRepository,
        quiz_builder: QuizBuilder,
        validator: Validator,
    ):
        self.admin_repo = admin_repo
        self.outage_repo = outage_repo
        self.validator = validator
        self.quiz_builder = quiz_builder

    async def upsert_quiz(self, quiz: schemas.Quiz):
        self.validator.validate_quiz(quiz)

        t0 = time.perf_counter()
        rd_quiz = self.quiz_builder.build_redis_quiz(quiz)
        t1 = time.perf_counter()
        await self.admin_repo.upsert_quiz(rd_quiz)
        t2 = time.perf_counter()

        logger.debug(f"upsert_quiz build={t1 - t0:.3f}s, redis={t2 - t1:.3f}s")

    async def read_all_answers(self):
        answer_keys, answers = await self.admin_repo.fetch_all_answers()
        return {
            RedisQuizKeys.extract_date(key): schemas.Answer.model_validate_json(ans)
            for key, ans in zip(answer_keys, answers)
        }

    async def delete_quiz(self, date: datetime.date):
        self.validator.validate_delete_date(date)
        redis_keys = RedisQuizKeys.from_date(date)
        deleted_cnt = await self.admin_repo.delete_quiz(redis_keys)
        self.validator.validate_deleted_cnt(deleted_cnt, len(fields(redis_keys)))

    # --- Outage Dates ---

    async def get_outage_dates(self) -> list[datetime.date]:
        return await self.outage_repo.fetch_all()

    async def create_outage_date(self, date: datetime.date) -> None:
        await self.outage_repo.insert(date)

    async def delete_outage_date(self, date: datetime.date) -> None:
        deleted = await self.outage_repo.delete(date)
        if not deleted:
            raise exc.OutageDateNotFound(f"Outage date {date} not found")
