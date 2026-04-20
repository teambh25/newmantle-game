from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configs(BaseSettings):
    admin_id: str
    admin_pw: str
    max_rank: int
    redis_url: str
    redis_max_conn: int
    allowed_origins: List[str] = []
    allowed_origin_regex: str = ""
    jwt_secret: str
    jwt_issuer: str
    database_url: str
    db_pool_size: int
    db_max_overflow: int
    test_redis_url: str = ""
    test_database_url: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


configs = Configs()
