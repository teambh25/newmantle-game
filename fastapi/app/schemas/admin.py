import datetime
from typing import Dict

from pydantic import BaseModel

from .common import Answer


class Quiz(BaseModel):
    date: datetime.date
    answer: Answer
    scores: Dict[str, float]  # {word: similarity score}
