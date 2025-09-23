import datetime

from fastapi import Depends
import redis.asyncio as redis

from app.features.game.service import GameService
from app.features.game.repository import GameRepo
import app.utils as utils
from .redis import get_redis_client


def get_game_repo(redis_client: redis.Redis = Depends(get_redis_client)):
    return GameRepo(redis_client)


def get_game_service(admin_repo: GameRepo = Depends(get_game_repo), today: datetime.date = Depends(utils.get_today_date)):
    return GameService(admin_repo, today)