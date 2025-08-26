from dataclasses import dataclass, fields
import datetime

import redis.asyncio as redis

def create_redis_pool(url: str, max_connection: int):
    pool = redis.ConnectionPool.from_url(
        url,
        max_connections=max_connection,
        decode_responses=True
    )
    return pool


@dataclass(frozen=True)
class RedisKeys:
    answers: str
    scores: str
    ranking: str
    NUM_KEYS = 3

    @classmethod
    def from_date(cls, date: datetime.date):
        return cls(
            answers=f"quiz:{date}:answers",
            scores=f"quiz:{date}:scores",
            ranking=f"quiz:{date}:ranking",
        )
    
    @staticmethod
    def extract_date_from_key(key: str):
        date = key.split(":")[1]
        return datetime.datetime.strptime(date, "%Y-%m-%d").date()
    