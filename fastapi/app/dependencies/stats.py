import datetime

import redis.asyncio as redis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

import app.utils as utils
from app.dependencies.database import get_db_session
from app.dependencies.redis import get_redis_client
from app.features.stats.repository import StatRepository
from app.features.stats.service import StatService


def get_stat_repo(
    session: AsyncSession = Depends(get_db_session),
) -> StatRepository:
    return StatRepository(session)


def get_stat_service(
    repo: StatRepository = Depends(get_stat_repo),
    redis_client: redis.Redis = Depends(get_redis_client),
    today: datetime.date = Depends(utils.get_today_date),
) -> StatService:
    return StatService(repo, redis_client, today)
