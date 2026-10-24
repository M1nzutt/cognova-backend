from pydantic import BaseModel

from app.schemas.activity_deadline_event_response import ActivityDeadlineEventResponse


class ActivityHistoryResponse(BaseModel):
    items: list[ActivityDeadlineEventResponse]
    next_after_revision: int | None
