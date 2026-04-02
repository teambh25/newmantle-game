import datetime

import pytest

import app.exceptions as exc
from app.cores.auth import UserIdentity
from app.features.stats.service import StatService

USER = UserIdentity(id="user-123", is_guest=False)
DATE = datetime.date(2025, 6, 15)


@pytest.fixture
def stat_service(mocker):
    stat_repo = mocker.AsyncMock()
    outage_repo = mocker.AsyncMock()
    today = DATE
    return StatService(stat_repo, outage_repo, today)


@pytest.mark.asyncio
class TestGetOverview:
    async def test_raises_when_start_date_after_end_date(self, stat_service):
        start = datetime.date(2025, 6, 10)
        end = datetime.date(2025, 6, 5)

        with pytest.raises(exc.InvalidDateRange):
            await stat_service.get_overview("user-1", start, end)

    async def test_allows_same_start_and_end_date(self, stat_service):
        date = datetime.date(2025, 6, 10)
        stat_service.stat_repo.fetch_all_results.return_value = {}
        stat_service.outage_repo.fetch_all.return_value = []

        await stat_service.get_overview("user-1", date, date)  # should not raise


@pytest.mark.asyncio
class TestRecordWithIdentity:
    async def test_record_guess_swallows_stat_record_error(self, stat_service):
        stat_service.stat_repo.record_guess.side_effect = exc.StatRecordError("fail")
        await stat_service.record_guess(USER, DATE, True)  # should not raise

    async def test_record_hint_swallows_stat_record_error(self, stat_service):
        stat_service.stat_repo.record_hint.side_effect = exc.StatRecordError("fail")
        await stat_service.record_hint(USER, DATE)  # should not raise

    async def test_record_giveup_swallows_stat_record_error(self, stat_service):
        stat_service.stat_repo.record_giveup.side_effect = exc.StatRecordError("fail")
        await stat_service.record_giveup(USER, DATE)  # should not raise
