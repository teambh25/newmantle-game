from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configs(BaseSettings):
    admin_id: str
    admin_pw: str
    max_rank: int
    redis_url: str
    max_connection: int
    allowed_origins: List[str] = []
    allowed_origin_regex: str = ""
    model_config = SettingsConfigDict(env_file='.env')


configs = Configs()