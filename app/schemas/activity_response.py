from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.activities.types import ActivityPriority, ActivityStatus


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subject_id: int
    title: str
    deadline: datetime
    priority: ActivityPriority
    status: ActivityStatus
    estimated_duration: int
    notes: str | None
    original_deadline: datetime
    deadline_revision: int
    created_at: datetime
    updated_at: datetime
