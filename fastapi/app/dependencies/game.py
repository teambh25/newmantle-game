import datetime

import redis.asyncio as redis
from fastapi import Depends

import app.utils as utils
from app.dependencies.redis import get_redis_client
from app.features.game.repository import GameRepo
from app.features.game.service import GameService


def get_game_repo(redis_client: redis.Redis = Depends(get_redis_client)):
    return GameRepo(redis_client)


def get_game_service(
    admin_repo: GameRepo = Depends(get_game_repo),
    today: datetime.date = Depends(utils.get_today_date),
):
    return GameService(admin_repo, today)
