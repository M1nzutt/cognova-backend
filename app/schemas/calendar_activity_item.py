from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.activities.types import ActivityPriority, ActivityStatus, Deadline


class CalendarActivityItem(BaseModel):
    """Projection of the original resource, identified by (type, id)."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    type: Literal["activity"] = "activity"
    title: str
    subject_id: int
    deadline: Deadline
    original_deadline: Deadline
    priority: ActivityPriority
    status: ActivityStatus
    estimated_duration: int
