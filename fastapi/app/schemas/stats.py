import datetime
import uuid
from enum import StrEnum

from pydantic import BaseModel


class CalendarStatus(StrEnum):
    SUCCESS_WITHOUT_HINT = "SUCCESS_WITHOUT_HINT"
    SUCCESS_WITH_HINT = "SUCCESS_WITH_HINT"
    FAIL = "FAIL"
    OUTAGE = "OUTAGE"


class CalendarEntry(BaseModel):
    date: datetime.date
    status: CalendarStatus


class StatSummary(BaseModel):
    total_success_days: int
    current_streak: int
    max_streak: int
    avg_guess_when_correct: float
    avg_hints_when_correct: float


class StatOverviewResp(BaseModel):
    calendar: list[CalendarEntry]
    summary: StatSummary


class UserType(StrEnum):
    USER = "user"
    GUEST = "guest"


class StatDailyResp(BaseModel):
    date: datetime.date
    status: str
    guess_count: int
    hint_count: int


class StatLinkReq(BaseModel):
    guest_id: uuid.UUID
