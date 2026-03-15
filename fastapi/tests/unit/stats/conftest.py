import datetime

import pytest

D = datetime.date


def make_entry(status: str, guess_count: int = 0, hint_count: int = 0) -> dict:
    """Create a result_map entry."""
    return {
        "status": status,
        "guess_count": guess_count,
        "hint_count": hint_count,
    }


@pytest.fixture
def success():
    return make_entry("SUCCESS", guess_count=5, hint_count=0)


@pytest.fixture
def success_with_hint():
    return make_entry("SUCCESS", guess_count=3, hint_count=2)


@pytest.fixture
def fail():
    return make_entry("FAIL", guess_count=10, hint_count=5)


@pytest.fixture
def giveup():
    return make_entry("GIVEUP", guess_count=7, hint_count=1)
