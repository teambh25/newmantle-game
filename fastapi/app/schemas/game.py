from pydantic import BaseModel

from .common import Answer


class GuessResp(BaseModel):
    correct: bool
    rank: int | None
    score: float | None
    answer: Answer | None


class HintResp(BaseModel):
    hint: str
    score: float | None


class GiveUpResp(Answer):
    pass
