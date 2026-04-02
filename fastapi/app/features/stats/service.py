import datetime
import uuid

from loguru import logger

import app.exceptions as exc
from app.cores.auth import UserIdentity
from app.features.common.repository import OutageDateRepository
from app.features.stats.calculator import (
    calc_current_streak,
    calc_max_streak,
    to_calendar_status,
)
from app.features.stats.dto import QuizResultEntry, ResultMap
from app.features.stats.repository import StatRepository
from app.models import UserQuizStatus
from app.schemas.stats import (
    CalendarEntry,
    CalendarStatus,
    StatSummary,
    UserType,
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
        self, identity: UserIdentity, quiz_date: datetime.date, is_correct: bool
    ) -> None:
        try:
            await self.stat_repo.record_guess(
                identity.id, identity.is_guest, quiz_date, is_correct
            )
        except exc.StatRecordError:
            logger.exception(f"stat record_guess failed for {identity.id}")

    async def record_hint(
        self, identity: UserIdentity, quiz_date: datetime.date
    ) -> None:
        try:
            await self.stat_repo.record_hint(identity.id, identity.is_guest, quiz_date)
        except exc.StatRecordError:
            logger.exception(f"stat record_hint failed for {identity.id}")

    async def record_giveup(
        self, identity: UserIdentity, quiz_date: datetime.date
    ) -> None:
        try:
            await self.stat_repo.record_giveup(
                identity.id, identity.is_guest, quiz_date
            )
        except exc.StatRecordError:
            logger.exception(f"stat record_giveup failed for {identity.id}")

    # --- Batch ---

    async def flush_to_db(self, quiz_date: datetime.date) -> tuple[int, int]:
        """Flush Redis stats for a given date to DB.

        Returns (flushed_count, skipped_count).
        """
        return await self.stat_repo.flush_stats(quiz_date)

    # --- Query ---

    async def get_overview(
        self, user_id: str, start_date: datetime.date, end_date: datetime.date
    ) -> tuple[list[CalendarEntry], StatSummary]:
        if start_date > end_date:
            raise exc.InvalidDateRange("start_date must not be after end_date")
        result_map = await self.stat_repo.fetch_all_results(user_id, end_date)
        outage_dates = set(await self.outage_repo.fetch_all())

        calendar = self._build_calendar(result_map, outage_dates, start_date, end_date)
        summary = self._build_summary(result_map, outage_dates, end_date)

        return calendar, summary

    async def get_daily(
        self, subject_id: uuid.UUID, user_type: UserType, quiz_date: datetime.date
    ) -> QuizResultEntry:
        stat = await self.stat_repo.fetch_stat(
            str(subject_id), is_guest=(user_type == UserType.GUEST), quiz_date=quiz_date
        )
        if stat is None:
            raise exc.StatNotFound(f"No stat found for {quiz_date}")
        return stat

    async def link_guest_stats(self, user_id: str, guest_id: uuid.UUID) -> None:
        await self.stat_repo.link_guest_stats(user_id, str(guest_id), self.today)

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
