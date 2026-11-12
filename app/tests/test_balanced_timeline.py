from datetime import datetime, timedelta, timezone
from random import Random

import pytest

from app.analytics.structures.balanced_timeline import BalancedTimeline
from app.analytics.structures.entries import TimelineEvent


def event(index: int) -> TimelineEvent:
    return TimelineEvent(
        occurred_at=datetime(2030, 1, 1, tzinfo=timezone.utc)
        + timedelta(minutes=index % 37),
        category=("activity", "study_session", "decision", "plan", "challenge")[
            index % 5
        ],
        resource_type="activity",
        resource_id=index + 1,
        occurrence_id=index + 1,
        event_type="planned",
    )


def test_balanced_timeline_orders_ranges_and_preserves_tree_invariants():
    index = BalancedTimeline()
    events = [event(value) for value in range(300)]
    Random(45).shuffle(events)
    for item in events:
        index.add(item)

    assert index.validate_invariants()
    ordered = sorted(events, key=lambda item: item.key)
    assert list(index.iter_range(limit=len(index))) == ordered
    start = datetime(2030, 1, 1, 0, 10, tzinfo=timezone.utc)
    end = datetime(2030, 1, 1, 0, 20, tzinfo=timezone.utc)
    expected = [item for item in ordered if start <= item.occurred_at < end]
    assert list(index.iter_range(start, end)) == expected
    assert list(index.iter_range(after_key=ordered[85].key, limit=10)) == ordered[86:96]


def test_balanced_timeline_rejects_duplicate_keys():
    index = BalancedTimeline()
    item = event(0)
    index.add(item)
    with pytest.raises(ValueError):
        index.add(item)
