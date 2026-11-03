from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.calendar_activity_item import CalendarActivityItem
from app.schemas.calendar_cursor import CalendarCursor
from app.schemas.calendar_study_session_item import CalendarStudySessionItem

CalendarItem = Annotated[
    CalendarActivityItem | CalendarStudySessionItem, Field(discriminator="type")
]


class CalendarResponse(BaseModel):
    items: list[CalendarItem]
    next_cursor: CalendarCursor | None
