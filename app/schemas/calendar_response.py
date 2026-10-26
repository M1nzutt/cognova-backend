from pydantic import BaseModel

from app.schemas.calendar_activity_item import CalendarActivityItem
from app.schemas.calendar_cursor import CalendarCursor


class CalendarResponse(BaseModel):
    items: list[CalendarActivityItem]
    next_cursor: CalendarCursor | None
