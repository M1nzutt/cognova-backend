from datetime import timezone

from sqlalchemy.orm import Session

from app.analytics.cursors import decode_timeline_cursor, encode_timeline_cursor
from app.analytics.structures.academic_archive import AcademicArchive
from app.analytics.structures.balanced_timeline import BalancedTimeline
from app.analytics.structures.entries import TimelineEvent
from app.analytics.structures.resource_directory import ResourceDirectory
from app.analytics.timeline_current_events import TimelineCurrentEvents
from app.analytics.timeline_historical_events import TimelineHistoricalEvents
from app.schemas.analytics_timeline_filters import AnalyticsTimelineFilters
from app.schemas.analytics_timeline_item import AnalyticsTimelineItem
from app.schemas.analytics_timeline_response import AnalyticsTimelineResponse


class AnalyticsTimelineService:
    """Merge owned historical and current source events into stable pages."""

    def __init__(self, db: Session) -> None:
        self._current_events = TimelineCurrentEvents(db)
        self._historical_events = TimelineHistoricalEvents(db)

    def get_page(
        self, user_id: int, filters: AnalyticsTimelineFilters
    ) -> AnalyticsTimelineResponse:
        start = filters.from_at.astimezone(timezone.utc)
        end = filters.to_at.astimezone(timezone.utc)
        after_key = (
            decode_timeline_cursor(filters.cursor, start, end, filters.category)
            if filters.cursor
            else None
        )
        history = AcademicArchive()
        current = BalancedTimeline()
        directory = ResourceDirectory()
        category = filters.category

        if category in (None, "activity"):
            self._current_events.activities(user_id, start, end, directory, current)
            self._historical_events.deadline_history(
                user_id, start, end, directory, history
            )
        if category in (None, "study_session"):
            self._current_events.planned_sessions(
                user_id, start, end, directory, current
            )
            self._historical_events.session_intervals(
                user_id, start, end, directory, history
            )
        if category in (None, "plan"):
            self._current_events.plans(user_id, start, end, directory, current)
        if category in (None, "decision"):
            self._historical_events.decisions(user_id, start, end, directory, history)
        if category in (None, "challenge"):
            self._current_events.challenges(user_id, start, end, directory, current)

        candidates = self._merge(
            list(history.iter_range(start, end, after_key, filters.limit + 1)),
            list(current.iter_range(start, end, after_key, filters.limit + 1)),
            filters.limit + 1,
        )
        has_more = len(candidates) > filters.limit
        page_events = candidates[: filters.limit]
        items = [self._to_item(event, directory) for event in page_events]
        next_cursor = (
            encode_timeline_cursor(page_events[-1], start, end, filters.category)
            if has_more and page_events
            else None
        )
        return AnalyticsTimelineResponse(items=items, next_cursor=next_cursor)

    @staticmethod
    def _merge(
        history: list[TimelineEvent],
        current: list[TimelineEvent],
        limit: int,
    ) -> list[TimelineEvent]:
        merged: list[TimelineEvent] = []
        left = right = 0
        while len(merged) < limit and (left < len(history) or right < len(current)):
            if right >= len(current) or (
                left < len(history) and history[left].key <= current[right].key
            ):
                merged.append(history[left])
                left += 1
            else:
                merged.append(current[right])
                right += 1
        return merged

    @staticmethod
    def _to_item(
        event: TimelineEvent, directory: ResourceDirectory
    ) -> AnalyticsTimelineItem:
        resource = directory.get((event.resource_type, event.resource_id))
        title = resource.title if resource is not None else "Recurso académico"
        subject_id = resource.subject_id if resource is not None else None
        subject = (
            directory.get(("subject", subject_id)) if subject_id is not None else None
        )
        if event.resource_type == "study_session":
            title = "Sesión de estudio"
        return AnalyticsTimelineItem(
            event_id=(
                f"{event.category}:{event.resource_id}:"
                f"{event.occurrence_id}:{event.event_type}"
            ),
            occurred_at=event.occurred_at.astimezone(timezone.utc),
            category=event.category,
            event_type=event.event_type,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            title=title,
            subject_id=subject_id,
            subject_name=subject.title if subject is not None else None,
            details=event.details,
        )


__all__ = ["AnalyticsTimelineService"]
