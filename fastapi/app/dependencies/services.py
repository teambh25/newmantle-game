import datetime

import redis.asyncio as redis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

import app.utils as utils
from app.cores.config import configs
from app.dependencies.database import get_db_session
from app.dependencies.redis import get_redis_client
from app.features.admin.quiz_builder import QuizBuilder
from app.features.admin.repository import AdminRepo
from app.features.admin.service import AdminService
from app.features.admin.validator import Validator
from app.features.common.repository import OutageDateRepository
from app.features.game.repository import GameRepo
from app.features.game.v2.service import GameServiceV2
from app.features.stats.repository import StatRepository
from app.features.stats.service import StatService

# ── Repositories ──────────────────────────────────────────────


def get_outage_repo(
    session: AsyncSession = Depends(get_db_session),
) -> OutageDateRepository:
    return OutageDateRepository(session)


def get_admin_repo(redis_client: redis.Redis = Depends(get_redis_client)):
    return AdminRepo(redis_client)


def get_game_repo(redis_client: redis.Redis = Depends(get_redis_client)):
    return GameRepo(redis_client)


def get_stat_repo(
    session: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> StatRepository:
    return StatRepository(session, redis_client)


# ── Services ─────────────────────────────────────────────────


def get_admin_service(
    admin_repo: AdminRepo = Depends(get_admin_repo),
    outage_repo: OutageDateRepository = Depends(get_outage_repo),
    today: datetime.date = Depends(utils.get_today_date),
):
    return AdminService(
        admin_repo=admin_repo,
        outage_repo=outage_repo,
        quiz_builder=QuizBuilder(configs.max_rank),
        validator=Validator(today, configs.max_rank),
    )


def get_game_service_v2(
    admin_repo: GameRepo = Depends(get_game_repo),
    today: datetime.date = Depends(utils.get_today_date),
):
    return GameServiceV2(admin_repo, today)


def get_stat_service(
    repo: StatRepository = Depends(get_stat_repo),
    outage_repo: OutageDateRepository = Depends(get_outage_repo),
    today: datetime.date = Depends(utils.get_today_date),
) -> StatService:
    return StatService(repo, outage_repo, today)
