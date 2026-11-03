from datetime import timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.activities.types import ActivityPriority, ActivityStatus, Deadline

CalendarItemType = Literal["activity", "study_session"]


class CalendarFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deadline_from: Deadline
    deadline_to: Deadline
    subject_id: Annotated[int | None, Field(gt=0, le=2147483647)] = None
    type: CalendarItemType | None = None
    status: ActivityStatus | None = None
    priority: ActivityPriority | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 50
    after_deadline: Deadline | None = None
    after_type: CalendarItemType | None = None
    after_id: Annotated[int | None, Field(gt=0, le=2147483647)] = None

    @field_validator("subject_id", "after_id", mode="before")
    @classmethod
    def reject_boolean_ids(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("IDs must be integers")
        return value

    @field_validator("limit", mode="before")
    @classmethod
    def reject_boolean_limit(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("Limit must be an integer")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> "CalendarFilters":
        span = self.deadline_to - self.deadline_from
        if not timedelta(0) < span <= timedelta(days=366):
            raise ValueError("Use a positive range of at most 366 days")
        has_deadline = self.after_deadline is not None
        has_id = self.after_id is not None
        if has_deadline != has_id or (self.after_type is not None and not has_id):
            raise ValueError("Both cursor fields are required")
        if self.type == "study_session" and (
            self.status is not None or self.priority is not None
        ):
            raise ValueError("Activity filters cannot be used with study_session")
        if self.after_deadline is not None and not (
            self.deadline_from <= self.after_deadline < self.deadline_to
        ):
            raise ValueError("Cursor must be inside the requested range")
        return self
