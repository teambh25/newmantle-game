import datetime

import redis.asyncio as redis
from fastapi import Depends

import app.utils as utils
from app.dependencies.redis import get_redis_client
from app.features.game.repository import GameRepo
from app.features.game.v1.service import GameServiceV1
from app.features.game.v2.service import GameServiceV2


def get_game_repo(redis_client: redis.Redis = Depends(get_redis_client)):
    return GameRepo(redis_client)


def get_game_service_v1(
    admin_repo: GameRepo = Depends(get_game_repo),
    today: datetime.date = Depends(utils.get_today_date),
):
    return GameServiceV1(admin_repo, today)


def get_game_service_v2(
    admin_repo: GameRepo = Depends(get_game_repo),
    today: datetime.date = Depends(utils.get_today_date),
):
    return GameServiceV2(admin_repo, today)
