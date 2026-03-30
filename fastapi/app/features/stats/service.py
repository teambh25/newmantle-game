import datetime

from loguru import logger

import app.exceptions as exc
from app.features.common.repository import OutageDateRepository
from app.features.stats.calculator import (
    calc_current_streak,
    calc_max_streak,
    to_calendar_status,
)
from app.features.stats.dto import ResultMap
from app.features.stats.repository import StatRepository
from app.models import UserQuizStatus
from app.schemas.stats import (
    CalendarEntry,
    CalendarStatus,
    StatDailyResp,
    StatOverviewResp,
    StatSummary,
)


class StatService:
    def __init__(
        self,
        stat_repo: StatRepository,
        outage_repo: OutageDateRepository,
        today: datetime.date,
    ):
        self.stat_repo = stat_repo
        self.outage_repo = outage_repo
        self.today = today

    # --- Recording (best-effort: infrastructure failure must not block game responses) ---

    async def record_guess(
        self, user_id: str | None, quiz_date: datetime.date, is_correct: bool
    ) -> None:
        if user_id is None:
            return
        try:
            await self.stat_repo.record_guess(user_id, quiz_date, is_correct)
        except exc.StatRecordError:
            logger.exception(f"stat record_guess failed for {user_id}")

    async def record_hint(self, user_id: str | None, quiz_date: datetime.date) -> None:
        if user_id is None:
            return
        try:
            await self.stat_repo.record_hint(user_id, quiz_date)
        except exc.StatRecordError:
            logger.exception(f"stat record_hint failed for {user_id}")

    async def record_giveup(
        self, user_id: str | None, quiz_date: datetime.date
    ) -> None:
        if user_id is None:
            return
        try:
            await self.stat_repo.record_giveup(user_id, quiz_date)
        except exc.StatRecordError:
            logger.exception(f"stat record_giveup failed for {user_id}")

    # --- Batch ---

    async def flush_to_db(self, quiz_date: datetime.date) -> tuple[int, int]:
        """Flush Redis stats for a given date to DB.

        Returns (flushed_count, skipped_count).
        """
        return await self.stat_repo.flush_stats(quiz_date)

    # --- Query ---

    async def get_overview(
        self, user_id: str, start_date: datetime.date, end_date: datetime.date
    ) -> StatOverviewResp:
        result_map = await self.stat_repo.fetch_all_results(user_id, end_date)
        outage_dates = set(await self.outage_repo.fetch_all())

        calendar = self._build_calendar(result_map, outage_dates, start_date, end_date)
        summary = self._build_summary(result_map, outage_dates, end_date)

        return StatOverviewResp(calendar=calendar, summary=summary)

    async def get_daily(self, user_id: str, quiz_date: datetime.date) -> StatDailyResp:
        stat = await self.stat_repo.fetch_stat(user_id, quiz_date)
        if stat is None:
            raise exc.StatNotFound(f"No stat found for {quiz_date}")
        return StatDailyResp(
            date=quiz_date,
            status=stat.status,
            guess_count=stat.guess_count,
            hint_count=stat.hint_count,
        )

    # --- Private helpers ---

    @staticmethod
    def _build_calendar(
        result_map: ResultMap,
        outage_dates: set[datetime.date],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> list[CalendarEntry]:
        """Build calendar entries for the requested date range."""
        calendar: list[CalendarEntry] = []

        for d, entry in result_map.items():
            if start_date <= d <= end_date:
                cal_status = to_calendar_status(
                    entry.status, entry.hint_count, d in outage_dates
                )
                calendar.append(CalendarEntry(date=d, status=cal_status))

        # Add OUTAGE entries for dates with no result record
        for od in outage_dates:
            if start_date <= od <= end_date and od not in result_map:
                calendar.append(CalendarEntry(date=od, status=CalendarStatus.OUTAGE))

        calendar.sort(key=lambda c: c.date)
        return calendar

    @staticmethod
    def _build_summary(
        result_map: ResultMap,
        outage_dates: set[datetime.date],
        end_date: datetime.date,
    ) -> StatSummary:
        """Calculate summary stats from all results."""
        total_success = 0
        total_guess = 0
        total_hints = 0

        for entry in result_map.values():
            if entry.status == UserQuizStatus.SUCCESS.value:
                total_success += 1
                total_guess += entry.guess_count
                total_hints += entry.hint_count

        avg_guess = round(total_guess / total_success, 2) if total_success else 0.0
        avg_hints = round(total_hints / total_success, 2) if total_success else 0.0

        return StatSummary(
            total_success_days=total_success,
            current_streak=calc_current_streak(result_map, outage_dates, end_date),
            max_streak=calc_max_streak(result_map, outage_dates),
            avg_guess_when_correct=avg_guess,
            avg_hints_when_correct=avg_hints,
        )
