from datetime import datetime, timedelta, timezone
from random import Random

import pytest

from app.analytics.structures.academic_archive import AcademicArchive
from app.analytics.structures.entries import TimelineEvent


def event(index: int) -> TimelineEvent:
    at = datetime(2030, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=index % 11)
    category = ("activity", "study_session", "decision", "plan", "challenge")[index % 5]
    return TimelineEvent(
        occurred_at=at,
        category=category,
        resource_type=category,
        resource_id=index + 1,
        occurrence_id=index + 1,
        event_type="created",
    )


def test_archive_orders_range_queries_and_pages_after_cursor():
    archive = AcademicArchive()
    events = [event(index) for index in range(180)]
    Random(24).shuffle(events)
    for item in events:
        archive.add(item)

    assert archive.validate_invariants()
    ordered = sorted(events, key=lambda item: item.key)
    expected = [
        item
        for item in ordered
        if datetime(2030, 1, 1, 0, 3, tzinfo=timezone.utc)
        <= item.occurred_at
        < datetime(2030, 1, 1, 0, 8, tzinfo=timezone.utc)
    ]
    assert (
        list(
            archive.iter_range(
                datetime(2030, 1, 1, 0, 3, tzinfo=timezone.utc),
                datetime(2030, 1, 1, 0, 8, tzinfo=timezone.utc),
            )
        )
        == expected
    )

    page = list(archive.iter_range(limit=17))
    all_pages = page[:]
    while len(all_pages) < len(archive):
        page = list(archive.iter_range(after_key=page[-1].key, limit=17))
        all_pages.extend(page)
    assert all_pages == ordered


def test_archive_rejects_duplicate_keys_and_invalid_ranges():
    archive = AcademicArchive()
    item = event(4)
    archive.add(item)
    with pytest.raises(ValueError):
        archive.add(item)
    with pytest.raises(ValueError):
        list(
            archive.iter_range(
                datetime(2030, 1, 2, tzinfo=timezone.utc),
                datetime(2030, 1, 1, tzinfo=timezone.utc),
            )
        )


def test_archive_detects_duplicates_across_a_root_split():
    archive = AcademicArchive()
    values = [event(index) for index in range(16)]
    ordered = sorted(values[:15], key=lambda item: item.key)
    for item in ordered:
        archive.add(item)
    archive.add(values[15])
    with pytest.raises(ValueError):
        archive.add(ordered[7])
    assert archive.validate_invariants()
