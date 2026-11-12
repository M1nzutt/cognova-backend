from datetime import datetime, timezone

from app.analytics.structures.entries import TimelineEvent
from app.analytics.timeline_service import AnalyticsTimelineService


def event(category: str, resource_id: int, event_type: str) -> TimelineEvent:
    return TimelineEvent(
        occurred_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        category=category,
        resource_type=category,
        resource_id=resource_id,
        occurrence_id=0,
        event_type=event_type,
    )


def test_timeline_merge_uses_category_rank_for_same_instant():
    historical = [
        event("activity", 4, "deadline_changed"),
        event("decision", 3, "decision"),
    ]
    planned = [
        event("study_session", 1, "planned"),
        event("plan", 2, "created"),
        event("challenge", 5, "created"),
    ]

    merged = AnalyticsTimelineService._merge(historical, planned, 10)

    assert [(item.category, item.resource_id) for item in merged] == [
        ("activity", 4),
        ("study_session", 1),
        ("decision", 3),
        ("plan", 2),
        ("challenge", 5),
    ]
    assert AnalyticsTimelineService._merge(historical, planned, 3) == merged[:3]
