from sqlalchemy import (
    DateTime,
    Integer,
    SmallInteger,
    Text,
    and_,
    case,
    cast,
    literal,
    null,
    or_,
    select,
    union_all,
)
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.study_session import StudySession
from app.schemas.calendar_activity_item import CalendarActivityItem
from app.schemas.calendar_cursor import CalendarCursor
from app.schemas.calendar_filters import CalendarFilters
from app.schemas.calendar_response import CalendarResponse
from app.schemas.calendar_study_session_item import CalendarStudySessionItem


class CalendarService:
    """Read original Cognova resources; never persist calendar events."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list(self, user_id: int, filters: CalendarFilters) -> CalendarResponse:
        sources = []
        if filters.type in (None, "activity"):
            sources.append(self._activities(user_id, filters))
        if filters.type in (None, "study_session") and (
            filters.status is None and filters.priority is None
        ):
            sources.append(self._sessions(user_id, filters))
        events = (
            union_all(*sources).subquery("calendar_items")
            if len(sources) > 1
            else sources[0].subquery("calendar_items")
        )
        event_type_rank = case((events.c.item_type == "activity", 0), else_=1)
        query = select(events)
        if filters.after_deadline is not None and filters.after_id is not None:
            cursor_type = filters.after_type or "activity"
            cursor_type_rank = 0 if cursor_type == "activity" else 1
            query = query.where(
                or_(
                    events.c.event_at > filters.after_deadline,
                    and_(
                        events.c.event_at == filters.after_deadline,
                        or_(
                            event_type_rank > cursor_type_rank,
                            and_(
                                event_type_rank == cursor_type_rank,
                                events.c.id > filters.after_id,
                            ),
                        ),
                    ),
                )
            )
        rows = (
            self._db.execute(
                query.order_by(events.c.event_at, event_type_rank, events.c.id).limit(
                    filters.limit + 1
                )
            )
            .mappings()
            .all()
        )
        items = [self._to_item(row) for row in rows[: filters.limit]]
        cursor = (
            CalendarCursor(
                after_deadline=rows[filters.limit - 1]["event_at"],
                after_type=rows[filters.limit - 1]["item_type"],
                after_id=rows[filters.limit - 1]["id"],
            )
            if len(rows) > filters.limit
            else None
        )
        return CalendarResponse(items=items, next_cursor=cursor)

    @staticmethod
    def _activities(user_id: int, filters: CalendarFilters):
        query = select(
            Activity.deadline.label("event_at"),
            literal("activity", type_=Text()).label("item_type"),
            Activity.id.label("id"),
            Activity.title.label("title"),
            Activity.subject_id.label("subject_id"),
            Activity.deadline.label("deadline"),
            Activity.original_deadline.label("original_deadline"),
            Activity.priority.label("priority"),
            Activity.status.label("status"),
            Activity.estimated_duration.label("estimated_duration"),
            cast(null(), Integer).label("activity_id"),
            cast(null(), DateTime(timezone=True)).label("planned_start_at"),
            cast(null(), SmallInteger).label("planned_duration"),
            cast(null(), Text).label("lifecycle"),
            cast(null(), Text).label("result"),
            cast(null(), DateTime(timezone=True)).label("start_at"),
            cast(null(), DateTime(timezone=True)).label("end_at"),
        ).where(
            Activity.user_id == user_id,
            Activity.deadline >= filters.deadline_from,
            Activity.deadline < filters.deadline_to,
        )
        if filters.subject_id is not None:
            query = query.where(Activity.subject_id == filters.subject_id)
        if filters.status is not None:
            query = query.where(Activity.status == filters.status)
        if filters.priority is not None:
            query = query.where(Activity.priority == filters.priority)
        return query

    @staticmethod
    def _sessions(user_id: int, filters: CalendarFilters):
        query = select(
            StudySession.planned_start_at.label("event_at"),
            literal("study_session", type_=Text()).label("item_type"),
            StudySession.id.label("id"),
            cast(null(), Text).label("title"),
            StudySession.subject_id.label("subject_id"),
            cast(null(), DateTime(timezone=True)).label("deadline"),
            cast(null(), DateTime(timezone=True)).label("original_deadline"),
            cast(null(), Text).label("priority"),
            cast(null(), Text).label("status"),
            cast(null(), SmallInteger).label("estimated_duration"),
            StudySession.activity_id.label("activity_id"),
            StudySession.planned_start_at.label("planned_start_at"),
            StudySession.planned_duration.label("planned_duration"),
            StudySession.execution_state.label("lifecycle"),
            StudySession.status.label("result"),
            StudySession.start_at.label("start_at"),
            StudySession.end_at.label("end_at"),
        ).where(
            StudySession.user_id == user_id,
            StudySession.planned_start_at >= filters.deadline_from,
            StudySession.planned_start_at < filters.deadline_to,
        )
        if filters.subject_id is not None:
            query = query.where(StudySession.subject_id == filters.subject_id)
        return query

    @staticmethod
    def _to_item(row):
        if row["item_type"] == "activity":
            return CalendarActivityItem(
                id=row["id"],
                title=row["title"],
                subject_id=row["subject_id"],
                deadline=row["deadline"],
                original_deadline=row["original_deadline"],
                priority=row["priority"],
                status=row["status"],
                estimated_duration=row["estimated_duration"],
            )
        return CalendarStudySessionItem(
            id=row["id"],
            subject_id=row["subject_id"],
            activity_id=row["activity_id"],
            planned_start_at=row["planned_start_at"],
            planned_duration=row["planned_duration"],
            lifecycle=row["lifecycle"],
            result=row["result"],
            start_at=row["start_at"],
            end_at=row["end_at"],
        )
