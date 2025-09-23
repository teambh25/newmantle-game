import datetime

from fastapi import Depends
import redis.asyncio as redis

from app.cores.config import configs
from app.features.admin.service import AdminService
from app.features.admin.repository import AdminRepo
import app.utils as utils
from .redis import get_redis_client


def get_admin_repo(redis_client: redis.Redis = Depends(get_redis_client)):
    return AdminRepo(redis_client)


def get_admin_service(admin_repo: AdminRepo = Depends(get_admin_repo), today: datetime.date = Depends(utils.get_today_date)):
    return AdminService(admin_repo, configs, today)