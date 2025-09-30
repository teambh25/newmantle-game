import datetime
from dataclasses import dataclass
from typing import Dict

from pydantic import BaseModel

from app.cores.redis import RedisKeys


class Answer(BaseModel):
    word: str
    tag: str
    description: str


class Quiz(BaseModel):
    date: datetime.date
    answer: str  # Answer
    scores: Dict[str, float]  # {word: similarity score}


@dataclass
class RedisQuizData:
    keys: RedisKeys
    answer_word: str
    scores_map: Dict[str, str]  # word -> score|rank
    ranking_map: Dict[int, str]  # rank -> word|score
    expire_at: datetime.datetime
