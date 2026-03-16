import datetime

from app.features.stats.dto import ResultMap
from app.models import UserQuizStatus
from app.schemas.stats import CalendarStatus


def to_calendar_status(status: str, hint_count: int, is_outage: bool) -> CalendarStatus:
    if is_outage:
        return CalendarStatus.OUTAGE
    if status == UserQuizStatus.SUCCESS.value:
        if hint_count > 0:
            return CalendarStatus.SUCCESS_WITH_HINT
        return CalendarStatus.SUCCESS_WITHOUT_HINT
    return CalendarStatus.FAIL


def calc_current_streak(
    result_map: ResultMap,
    outage_dates: set[datetime.date],
    end_date: datetime.date,
) -> int:
    """Count consecutive SUCCESS days backwards from end_date."""
    end_entry = result_map.get(end_date)
    current = end_date
    if not end_entry or end_entry.status != UserQuizStatus.SUCCESS.value:
        current = end_date - datetime.timedelta(days=1)

    streak = 0
    while True:
        if current in outage_dates:
            current -= datetime.timedelta(days=1)
            continue
        entry = result_map.get(current)
        if entry and entry.status == UserQuizStatus.SUCCESS.value:
            streak += 1
            current -= datetime.timedelta(days=1)
        else:
            break
    return streak


def calc_max_streak(
    result_map: ResultMap,
    outage_dates: set[datetime.date],
) -> int:
    """Find the longest consecutive SUCCESS streak across all history."""
    max_streak = 0
    streak = 0
    prev_date: datetime.date | None = None

    for d in sorted(result_map.keys()):
        if d in outage_dates:
            continue

        if result_map[d].status == UserQuizStatus.SUCCESS.value:
            if prev_date is not None and _has_gap(prev_date, d, outage_dates):
                streak = 0
            streak += 1
            prev_date = d
        else:
            streak = 0

        if streak > max_streak:
            max_streak = streak

    return max_streak


def _has_gap(
    prev_date: datetime.date,
    curr_date: datetime.date,
    outage_dates: set[datetime.date],
) -> bool:
    """Check if there's a non-outage gap between two dates."""
    d = prev_date + datetime.timedelta(days=1)
    while d < curr_date:
        if d not in outage_dates:
            return True
        d += datetime.timedelta(days=1)
    return False
