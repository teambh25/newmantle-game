import datetime

import redis.asyncio as redis
from fastapi import Depends

import app.utils as utils
from app.cores.config import configs
from app.dependencies.redis import get_redis_client
from app.features.admin.quiz_builder import QuizBuilder
from app.features.admin.repository import AdminRepo
from app.features.admin.service import AdminService
from app.features.admin.validator import Validator


def get_admin_repo(redis_client: redis.Redis = Depends(get_redis_client)):
    return AdminRepo(redis_client)


def get_admin_service(
    admin_repo: AdminRepo = Depends(get_admin_repo),
    today: datetime.date = Depends(utils.get_today_date),
):
    return AdminService(
        admin_repo=admin_repo,
        quiz_builder=QuizBuilder(configs.max_rank),
        validator=Validator(today, configs.max_rank),
    )
