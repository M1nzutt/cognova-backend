from pydantic import BaseModel

from app.activities.types import Deadline, EntityId
from app.schemas.calendar_filters import CalendarItemType


class CalendarCursor(BaseModel):
    after_deadline: Deadline
    after_type: CalendarItemType
    after_id: EntityId
