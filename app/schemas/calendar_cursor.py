from pydantic import BaseModel

from app.activities.types import Deadline, EntityId


class CalendarCursor(BaseModel):
    after_deadline: Deadline
    after_id: EntityId
