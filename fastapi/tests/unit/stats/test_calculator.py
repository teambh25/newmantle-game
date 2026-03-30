"""Unit tests for features/stats/calculator.py

Suites 10, 13-15 from docs/user-stats-test-plan.md.
"""

import datetime

from app.features.stats.calculator import (
    calc_current_streak,
    calc_max_streak,
    to_calendar_status,
)
from app.schemas.stats import CalendarStatus
from tests.unit.stats.conftest import make_entry

D = datetime.date  # Alias

# ---------------------------------------------------------------------------
# Suite 10: to_calendar_status
# ---------------------------------------------------------------------------


class TestToCalendarStatus:
    def test_success_without_hint(self):
        assert (
            to_calendar_status("SUCCESS", 0, False)
            == CalendarStatus.SUCCESS_WITHOUT_HINT
        )

    def test_success_with_hint(self):
        assert (
            to_calendar_status("SUCCESS", 2, False) == CalendarStatus.SUCCESS_WITH_HINT
        )

    def test_fail(self):
        assert to_calendar_status("FAIL", 0, False) == CalendarStatus.FAIL

    def test_giveup_treated_as_fail(self):
        assert to_calendar_status("GIVEUP", 1, False) == CalendarStatus.FAIL

    def test_outage_overrides_success(self):
        assert to_calendar_status("SUCCESS", 0, True) == CalendarStatus.OUTAGE


# ---------------------------------------------------------------------------
# Suite 11: calc_current_streak
# ---------------------------------------------------------------------------


class TestCalcCurrentStreak:
    def test_end_date_is_success(self):
        result_map = {
            D(2026, 3, 11): make_entry("FAIL"),
            D(2026, 3, 12): make_entry("SUCCESS"),
            D(2026, 3, 13): make_entry("SUCCESS"),
        }
        assert calc_current_streak(result_map, set(), D(2026, 3, 13)) == 2

    def test_end_date_is_fail(self):
        result_map = {
            D(2026, 3, 11): make_entry("SUCCESS"),
            D(2026, 3, 12): make_entry("SUCCESS"),
            D(2026, 3, 13): make_entry("FAIL"),
        }
        assert calc_current_streak(result_map, set(), D(2026, 3, 13)) == 2

    def test_end_date_no_record(self):
        result_map = {
            D(2026, 3, 12): make_entry("SUCCESS"),
        }
        assert calc_current_streak(result_map, set(), D(2026, 3, 13)) == 1

    def test_skip_outage_date(self):
        result_map = {
            D(2026, 3, 11): make_entry("SUCCESS"),
            D(2026, 3, 13): make_entry("SUCCESS"),
        }
        outage = {D(2026, 3, 12)}
        assert calc_current_streak(result_map, outage, D(2026, 3, 13)) == 2

    def test_outage_date_with_success_record(self):
        # 3/12: outage before record was left — ignored for fairness
        result_map = {
            D(2026, 3, 11): make_entry("SUCCESS"),
            D(2026, 3, 12): make_entry("SUCCESS"),
            D(2026, 3, 13): make_entry("SUCCESS"),
        }
        outage = {D(2026, 3, 12)}
        assert calc_current_streak(result_map, outage, D(2026, 3, 13)) == 2

    def test_outage_date_with_fail_record(self):
        # 3/12: outage before record was left — ignored for fairness
        result_map = {
            D(2026, 3, 11): make_entry("SUCCESS"),
            D(2026, 3, 12): make_entry("FAIL"),
            D(2026, 3, 13): make_entry("SUCCESS"),
        }
        outage = {D(2026, 3, 12)}
        assert calc_current_streak(result_map, outage, D(2026, 3, 13)) == 2

    def test_outage_date_with_giveup_record(self):
        # 3/12: outage before record was left — ignored for fairness
        result_map = {
            D(2026, 3, 11): make_entry("SUCCESS"),
            D(2026, 3, 12): make_entry("GIVEUP"),
            D(2026, 3, 13): make_entry("SUCCESS"),
        }
        outage = {D(2026, 3, 12)}
        assert calc_current_streak(result_map, outage, D(2026, 3, 13)) == 2

    def test_gap_breaks_streak(self):
        # 3/12 has no record and is not an outage — streak resets
        result_map = {
            D(2026, 3, 11): make_entry("SUCCESS"),
            D(2026, 3, 13): make_entry("SUCCESS"),
        }
        assert calc_current_streak(result_map, set(), D(2026, 3, 13)) == 1

    def test_only_outage_no_records(self):
        # Outage dates are skipped, but no SUCCESS records → streak=0
        outage = {D(2026, 3, 11), D(2026, 3, 12)}
        assert calc_current_streak({}, outage, D(2026, 3, 13)) == 0

    def test_empty_result_map(self):
        assert calc_current_streak({}, set(), D(2026, 3, 13)) == 0

    def test_all_success(self):
        result_map = {
            D(2026, 3, 11): make_entry("SUCCESS"),
            D(2026, 3, 12): make_entry("SUCCESS"),
            D(2026, 3, 13): make_entry("SUCCESS"),
        }
        assert calc_current_streak(result_map, set(), D(2026, 3, 13)) == 3


# ---------------------------------------------------------------------------
# Suite 12: calc_max_streak
# ---------------------------------------------------------------------------


class TestCalcMaxStreak:
    def test_no_record_no_outage_breaks_streak(self):
        # 3/11 has no record and is not outage — gap between 3/10 and 3/12 breaks streak
        result_map = {
            D(2026, 3, 10): make_entry("SUCCESS"),
            D(2026, 3, 12): make_entry("SUCCESS"),
        }
        assert calc_max_streak(result_map, set()) == 1

    def test_single_streak(self):
        result_map = {
            D(2026, 3, 10): make_entry("SUCCESS"),
            D(2026, 3, 11): make_entry("SUCCESS"),
            D(2026, 3, 12): make_entry("SUCCESS"),
            D(2026, 3, 13): make_entry("SUCCESS"),
        }
        assert calc_max_streak(result_map, set()) == 4

    def test_multiple_streaks_returns_max(self):
        result_map = {
            D(2026, 3, 10): make_entry("SUCCESS"),
            D(2026, 3, 11): make_entry("SUCCESS"),
            D(2026, 3, 12): make_entry("FAIL"),
            D(2026, 3, 13): make_entry("SUCCESS"),
            D(2026, 3, 14): make_entry("SUCCESS"),
            D(2026, 3, 15): make_entry("SUCCESS"),
            D(2026, 3, 16): make_entry("SUCCESS"),
        }
        assert calc_max_streak(result_map, set()) == 4

    def test_outage_does_not_break_streak(self):
        result_map = {
            D(2026, 3, 10): make_entry("SUCCESS"),
            D(2026, 3, 12): make_entry("SUCCESS"),
        }
        outage = {D(2026, 3, 11)}
        assert calc_max_streak(result_map, outage) == 2

    def test_outage_with_success_record_ignored(self):
        # 3/11: outage before record was left — ignored for fairness
        result_map = {
            D(2026, 3, 10): make_entry("SUCCESS"),
            D(2026, 3, 11): make_entry("SUCCESS"),
            D(2026, 3, 12): make_entry("SUCCESS"),
        }
        outage = {D(2026, 3, 11)}
        assert calc_max_streak(result_map, outage) == 2

    def test_outage_with_fail_record_ignored(self):
        # 3/11: outage before record was left — ignored for fairness
        result_map = {
            D(2026, 3, 10): make_entry("SUCCESS"),
            D(2026, 3, 11): make_entry("FAIL"),
            D(2026, 3, 12): make_entry("SUCCESS"),
        }
        outage = {D(2026, 3, 11)}
        assert calc_max_streak(result_map, outage) == 2

    def test_outage_with_giveup_record_ignored(self):
        # 3/11: outage before record was left — ignored for fairness
        result_map = {
            D(2026, 3, 10): make_entry("SUCCESS"),
            D(2026, 3, 11): make_entry("GIVEUP"),
            D(2026, 3, 12): make_entry("SUCCESS"),
        }
        outage = {D(2026, 3, 11)}
        assert calc_max_streak(result_map, outage) == 2

    def test_only_outage_no_records(self):
        # Outage dates are skipped, but no SUCCESS records → max=0
        outage = {D(2026, 3, 10), D(2026, 3, 11)}
        assert calc_max_streak({}, outage) == 0

    def test_gap_breaks_streak(self):
        # 3/11 has no record and is not an outage — streak resets
        result_map = {
            D(2026, 3, 10): make_entry("SUCCESS"),
            D(2026, 3, 12): make_entry("SUCCESS"),
        }
        assert calc_max_streak(result_map, set()) == 1

    def test_empty_result_map(self):
        assert calc_max_streak({}, set()) == 0

    def test_all_fail(self):
        result_map = {
            D(2026, 3, 10): make_entry("FAIL"),
            D(2026, 3, 11): make_entry("FAIL"),
            D(2026, 3, 12): make_entry("FAIL"),
        }
        assert calc_max_streak(result_map, set()) == 0
