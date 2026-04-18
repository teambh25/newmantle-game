import datetime

import pytest

from app.features.common.redis_keys import RedisQuizKeys


@pytest.mark.parametrize(
    "days_ago, expected",
    [
        (0, False),  # today
        (1, False),  # yesterday — last valid day (TTL_DAYS=2)
        (2, True),  # 2 days ago — first expired day
        (3, True),  # further past
    ],
)
def test_is_expired(days_ago, expected):
    today = datetime.date(2025, 8, 29)
    date = today - datetime.timedelta(days=days_ago)
    assert RedisQuizKeys.is_expired(date, today) == expected
