from datetime import timedelta
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.activities.types import ActivityPriority, ActivityStatus, Deadline


class CalendarFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deadline_from: Deadline
    deadline_to: Deadline
    subject_id: Annotated[int | None, Field(gt=0, le=2147483647)] = None
    status: ActivityStatus | None = None
    priority: ActivityPriority | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 50
    after_deadline: Deadline | None = None
    after_id: Annotated[int | None, Field(gt=0, le=2147483647)] = None

    @model_validator(mode="after")
    def validate_window(self) -> "CalendarFilters":
        span = self.deadline_to - self.deadline_from
        if not timedelta(0) < span <= timedelta(days=366):
            raise ValueError("Use a positive range of at most 366 days")
        if (self.after_deadline is None) != (self.after_id is None):
            raise ValueError("Both cursor fields are required")
        if self.after_deadline is not None and not (
            self.deadline_from <= self.after_deadline < self.deadline_to
        ):
            raise ValueError("Cursor must be inside the requested range")
        return self
