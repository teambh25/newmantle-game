import datetime
from typing import Dict

from pydantic import BaseModel

class Quiz(BaseModel):
    date: datetime.date
    scores: Dict[str, float]