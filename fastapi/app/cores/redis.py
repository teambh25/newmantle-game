import datetime
from dataclasses import dataclass
from typing import Dict

import redis.asyncio as redis

ANSWER_INDICATOR = "answer"
DELIMITER = "|"


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
    def extract_date(key: str):
        date = key.split(":")[1]
        return datetime.datetime.strptime(date, "%Y-%m-%d").date()


@dataclass
class RedisQuizData:
    keys: RedisKeys
    answer: str  # json string of Answer class
    scores_map: Dict[str, str]  # word -> score|rank
    ranking_map: Dict[int, str]  # rank -> word|score
    expire_at: datetime.datetime

    @staticmethod
    def serialize_score_and_rank(score: float, rank: int):
        return f"{score:.2f}{DELIMITER}{rank}"

    @staticmethod
    def serialize_word_and_score(word: str, score: float):
        return f"{word}{DELIMITER}{score:.2f}"

    @staticmethod
    def deserialize_score_and_rank(score_rank: str):
        score, rank = score_rank.split(DELIMITER)
        return float(score), int(rank)

    @staticmethod
    def deserialize_word_and_score(word_score: str):
        word, score = word_score.split(DELIMITER)
        return word, float(score)
