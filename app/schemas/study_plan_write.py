from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.study_plans.validation import has_disallowed_controls, normalize_text
from app.study_sessions.types import EntityId, Instant


class StudyPlanWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str, BeforeValidator(normalize_text), Field(min_length=1, max_length=100)
    ]
    objective: Annotated[
        str, BeforeValidator(normalize_text), Field(min_length=1, max_length=2000)
    ]
    start_at: Instant
    end_at: Instant
    subject_ids: Annotated[list[EntityId], Field(min_length=1, max_length=100)]
    activity_ids: Annotated[list[EntityId], Field(max_length=200)] = Field(
        default_factory=list
    )
    study_session_ids: Annotated[list[EntityId], Field(max_length=200)] = Field(
        default_factory=list
    )

    @field_validator("name", "objective")
    @classmethod
    def text_controls(cls, value: str) -> str:
        if has_disallowed_controls(value):
            raise ValueError("Invalid control characters")
        return value

    @field_validator("subject_ids", "activity_ids", "study_session_ids")
    @classmethod
    def unique_ids(cls, values: list[int]) -> list[int]:
        if len(values) != len(set(values)):
            raise ValueError("Resource identifiers must be unique")
        return values

    @model_validator(mode="after")
    def increasing_dates(self) -> "StudyPlanWrite":
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be later than start_at")
        return self


__all__ = ["StudyPlanWrite"]
