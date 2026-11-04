from datetime import datetime, timezone

import pytest

from app.study_plans.weekly_rhythm import WeeklyRhythm


def test_weekly_rhythm_links_monday_and_sunday_in_both_directions():
    rhythm = WeeklyRhythm()

    assert rhythm.previous_day(0).weekday == 6
    assert rhythm.next_day(6).weekday == 0
    assert [day["weekday"] for day in rhythm.totals(5)] == [5, 6, 0, 1, 2, 3, 4]


def test_weekly_rhythm_accumulates_session_minutes_by_weekday():
    rhythm = WeeklyRhythm()
    rhythm.add_session(datetime(2030, 1, 7, tzinfo=timezone.utc), 45)
    rhythm.add_session(datetime(2030, 1, 7, 9, tzinfo=timezone.utc), 30)

    assert rhythm.totals()[0]["planned_minutes"] == 75
    assert sum(day["planned_minutes"] for day in rhythm.totals()) == 75
    with pytest.raises(ValueError):
        rhythm.add_session(datetime(2030, 1, 7, tzinfo=timezone.utc), 0)
