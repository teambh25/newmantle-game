import dataclasses
import datetime


@dataclasses.dataclass(frozen=True)
class QuizResultEntry:
    status: str
    guess_count: int
    hint_count: int


# {date: QuizResultEntry}
ResultMap = dict[datetime.date, QuizResultEntry]
