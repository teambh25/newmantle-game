import datetime
from typing import Dict

from pydantic import BaseModel

from .common import Answer


class Quiz(BaseModel):
    date: datetime.date
    answer: Answer
    scores: Dict[str, float]  # {word: similarity score}


class OutageDateRequest(BaseModel):
    date: datetime.date


class OutageDateListResp(BaseModel):
    outage_dates: list[datetime.date]
