from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.study_sessions.types import (
    Instant,
    SessionExecutionState,
    SessionResult,
)


class StudySessionFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: Annotated[int, Field(gt=0, le=2147483647)] | None = None
    activity_id: Annotated[int, Field(gt=0, le=2147483647)] | None = None
    execution_state: SessionExecutionState | None = None
    status: SessionResult | None = None
    planned_start_from: Instant | None = None
    planned_start_to: Instant | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 50
    after_planned_start_at: Instant | None = None
    after_id: Annotated[int, Field(gt=0, le=2147483647)] | None = None

    @field_validator("subject_id", "activity_id", "after_id", mode="before")
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
    def validate_range_and_cursor(self) -> "StudySessionFilters":
        if (
            self.planned_start_from is not None
            and self.planned_start_to is not None
            and self.planned_start_from >= self.planned_start_to
        ):
            raise ValueError("Invalid planned start range")
        if (self.after_planned_start_at is None) != (self.after_id is None):
            raise ValueError("Cursor fields must be supplied together")
        if self.after_planned_start_at is not None:
            if (
                self.planned_start_from is not None
                and self.after_planned_start_at < self.planned_start_from
            ):
                raise ValueError("Cursor precedes planned start range")
            if (
                self.planned_start_to is not None
                and self.after_planned_start_at >= self.planned_start_to
            ):
                raise ValueError("Cursor is outside planned start range")
        return self
