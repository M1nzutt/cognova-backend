from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.schemas.calendar_activity_item import CalendarActivityItem
from app.schemas.calendar_cursor import CalendarCursor
from app.schemas.calendar_filters import CalendarFilters
from app.schemas.calendar_response import CalendarResponse


class CalendarService:
    """Read original Cognova resources; never persist calendar events."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list(self, user_id: int, filters: CalendarFilters) -> CalendarResponse:
        query = select(Activity).where(
            Activity.user_id == user_id,
            Activity.deadline >= filters.deadline_from,
            Activity.deadline < filters.deadline_to,
        )
        for field in ("subject_id", "status", "priority"):
            value = getattr(filters, field)
            if value is not None:
                query = query.where(getattr(Activity, field) == value)
        if filters.after_deadline is not None and filters.after_id is not None:
            query = query.where(
                or_(
                    Activity.deadline > filters.after_deadline,
                    and_(
                        Activity.deadline == filters.after_deadline,
                        Activity.id > filters.after_id,
                    ),
                )
            )
        rows = self._db.scalars(
            query.order_by(Activity.deadline, Activity.id).limit(filters.limit + 1)
        ).all()
        items = [CalendarActivityItem.model_validate(r) for r in rows[: filters.limit]]
        cursor = (
            CalendarCursor(after_deadline=items[-1].deadline, after_id=items[-1].id)
            if len(rows) > filters.limit
            else None
        )
        return CalendarResponse(items=items, next_cursor=cursor)
