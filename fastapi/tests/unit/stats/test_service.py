import datetime

import pytest

import app.exceptions as exc
from app.features.stats.service import StatService


@pytest.fixture
def stat_service(mocker):
    stat_repo = mocker.AsyncMock()
    outage_repo = mocker.AsyncMock()
    today = datetime.date(2025, 6, 15)
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

        result = await stat_service.get_overview("user-1", date, date)

        assert result.calendar == []
