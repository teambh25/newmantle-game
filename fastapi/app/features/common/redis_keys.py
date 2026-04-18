import datetime
from dataclasses import dataclass
from typing import ClassVar, Dict
from zoneinfo import ZoneInfo

ANSWER_INDICATOR = "answer"


@dataclass(frozen=True)
class RedisQuizKeys:
    TTL_DAYS: ClassVar[int] = 2

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

    @classmethod
    def get_expiry(cls, date: datetime.date) -> datetime.datetime:
        # 5-minute buffer after midnight KST to handle in-flight requests
        return datetime.datetime.combine(
            date + datetime.timedelta(days=cls.TTL_DAYS),
            datetime.time(hour=0, minute=5, second=0, tzinfo=ZoneInfo("Asia/Seoul")),
        )

    @classmethod
    def is_expired(cls, date: datetime.date, today: datetime.date) -> bool:
        return (today - date).days >= cls.TTL_DAYS

    @staticmethod
    def extract_date(key: str):
        date = key.split(":")[1]
        return datetime.datetime.strptime(date, "%Y-%m-%d").date()


@dataclass
class RedisQuizData:
    keys: RedisQuizKeys
    answer: str  # json string of Answer class
    scores_map: Dict[str, str]  # word -> score|rank
    ranking_map: Dict[int, str]  # rank -> word|score
    expire_at: datetime.datetime

    @staticmethod
    def serialize_score_and_rank(score: float, rank: int):
        return f"{score:.2f}|{rank}"

    @staticmethod
    def serialize_word_and_score(word: str, score: float):
        return f"{word}|{score:.2f}"

    @staticmethod
    def deserialize_score_and_rank(score_rank: str):
        score, rank = score_rank.split("|")
        return float(score), int(rank)

    @staticmethod
    def deserialize_word_and_score(word_score: str):
        word, score = word_score.split("|")
        return word, float(score)


@dataclass(frozen=True)
class RedisStatKeys:
    TTL_DAYS: ClassVar[int] = 7

    key: str
    ttl: int = 60 * 60 * 24 * TTL_DAYS

    @classmethod
    def from_user_and_date(cls, user_id: str, date: datetime.date):
        return cls(key=f"user:{user_id}:quiz:{date}:stat")

    @classmethod
    def from_guest_and_date(cls, guest_id: str, date: datetime.date):
        return cls(key=f"guest:{guest_id}:quiz:{date}:stat")
