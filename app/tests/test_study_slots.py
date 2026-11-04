from datetime import datetime, timedelta, timezone

import pytest

from app.study_plans.schedule_entry import ScheduleEntry
from app.study_plans.study_slots import StudySlots


def test_study_slots_sorts_reservations_and_finds_unoccupied_candidates():
    slots = StudySlots()
    monday = datetime(2030, 1, 7, 9, tzinfo=timezone.utc)
    slots.reserve(ScheduleEntry(monday + timedelta(hours=2), monday + timedelta(hours=3), 2, "study_session"))
    slots.reserve(ScheduleEntry(monday, monday + timedelta(hours=1), 1, "study_session"))

    assert [entry.reference_id for entry in slots.entries()] == [1, 2]
    candidates = slots.available_slots(monday, monday + timedelta(hours=4), 30)
    assert [(entry.start_at, entry.end_at) for entry in candidates] == [
        (monday + timedelta(hours=1), monday + timedelta(hours=1, minutes=30)),
        (monday + timedelta(hours=3), monday + timedelta(hours=3, minutes=30)),
    ]


def test_study_slots_rejects_overlap_invalid_ranges_and_capacity_overflow():
    slots = StudySlots(capacity=1)
    start = datetime(2030, 1, 7, 9, tzinfo=timezone.utc)
    slots.reserve(ScheduleEntry(start, start + timedelta(minutes=30), 1, "study_session"))
    with pytest.raises(ValueError, match="overlaps"):
        slots.reserve(
            ScheduleEntry(
                start + timedelta(minutes=15),
                start + timedelta(minutes=45),
                2,
                "study_session",
            )
        )
    with pytest.raises(OverflowError):
        slots.reserve(
            ScheduleEntry(
                start + timedelta(hours=1),
                start + timedelta(hours=2),
                3,
                "study_session",
            )
        )
    with pytest.raises(ValueError):
        slots.available_slots(start, start, 30)
