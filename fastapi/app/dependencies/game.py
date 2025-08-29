from fastapi import Depends
import redis.asyncio as redis

from app.cores.config import settings
from app.features.game.service import GameService
from app.features.game.repository import GameRepo
from .redis import get_redis_client


def get_game_repo(redis_client: redis.Redis = Depends(get_redis_client)):
    return GameRepo(redis_client)


def get_game_service(admin_repo: GameRepo = Depends(get_game_repo)):
    return GameService(admin_repo, settings)