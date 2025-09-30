import datetime
from dataclasses import dataclass

import redis.asyncio as redis

ANSWER_INDICATOR = "answer"


def create_redis_pool(url: str, max_connection: int):
    pool = redis.ConnectionPool.from_url(
        url,
        max_connections=max_connection,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        # socket_keepalive=True,
    )
    return pool


@dataclass(frozen=True)
class RedisKeys:
    answers_key: str
    scores_key: str
    ranking_key: str

    @classmethod
    def from_date(cls, date: datetime.date):
        return cls(
            answers_key=f"quiz:{date}:answers",
            scores_key=f"quiz:{date}:scores",
            ranking_key=f"quiz:{date}:ranking",
        )

    @staticmethod
    def extract_date_from_key(key: str):
        date = key.split(":")[1]
        return datetime.datetime.strptime(date, "%Y-%m-%d").date()
