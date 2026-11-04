from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.study_plans.validation import (
    has_disallowed_controls,
    json_size,
    normalize_text,
)
from app.study_sessions.types import EntityId, Instant

ChallengeTarget = Literal[
    "study_minutes",
    "activity_completion",
    "session_completion",
    "subject_mastery",
    "custom",
]


class StudyChallengeWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: EntityId | None = None
    activity_id: EntityId | None = None
    study_session_id: EntityId | None = None
    title: Annotated[
        str, BeforeValidator(normalize_text), Field(min_length=1, max_length=100)
    ]
    description: Annotated[
        str, BeforeValidator(normalize_text), Field(min_length=1, max_length=2000)
    ]
    target_type: ChallengeTarget
    target_value: dict[str, Any]
    start_at: Instant | None = None
    deadline: Instant | None = None
    generation_criteria: dict[str, Any]
    depends_on_activity_ids: Annotated[list[EntityId], Field(max_length=100)] = Field(
        default_factory=list
    )

    @field_validator("title", "description")
    @classmethod
    def text_controls(cls, value: str) -> str:
        if has_disallowed_controls(value):
            raise ValueError("Invalid control characters")
        return value

    @field_validator("depends_on_activity_ids")
    @classmethod
    def unique_dependencies(cls, values: list[int]) -> list[int]:
        if len(values) != len(set(values)):
            raise ValueError("Dependency identifiers must be unique")
        return values

    @field_validator("generation_criteria")
    @classmethod
    def valid_criteria(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value or json_size(value) > 16384:
            raise ValueError("Generation criteria must be a small non-empty object")
        if "depends_on_activity_ids" in value:
            raise ValueError("Dependency identifiers use their dedicated field")
        return value

    @field_validator("target_value")
    @classmethod
    def valid_target_value(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value or json_size(value) > 4096:
            raise ValueError("Target value must be a small non-empty object")
        return value

    @model_validator(mode="after")
    def validate_target_context(self) -> "StudyChallengeWrite":
        value = self.target_value
        if self.target_type == "study_minutes":
            minutes = value.get("minutes")
            if (
                self.subject_id is None and self.study_session_id is None
            ) or set(value) != {"minutes"} or type(minutes) is not int or not 1 <= minutes <= 1440:
                raise ValueError("study_minutes requires a contextual 1–1440 minute target")
        elif self.target_type == "activity_completion":
            if self.activity_id is None or value != {"status": "completed"}:
                raise ValueError("activity_completion requires a completed activity target")
        elif self.target_type == "session_completion":
            if self.study_session_id is None or value != {"lifecycle": "finished"}:
                raise ValueError("session_completion requires a finished session target")
        elif self.target_type == "subject_mastery":
            criterion = value.get("criterion")
            threshold = value.get("threshold")
            if (
                self.subject_id is None
                or set(value) != {"criterion", "threshold"}
                or not isinstance(criterion, str)
                or not criterion.strip()
                or len(criterion.strip()) > 200
                or type(threshold) is not int
                or not 1 <= threshold <= 100
            ):
                raise ValueError("subject_mastery requires a criterion and a 1–100 threshold")
        elif self.target_type == "custom" and not value:
            raise ValueError("custom target cannot be empty")
        if (
            self.start_at is not None
            and self.deadline is not None
            and self.deadline < self.start_at
        ):
            raise ValueError("deadline must not be before start_at")
        if self.subject_id is None and (
            self.activity_id is not None or self.study_session_id is not None
        ):
            raise ValueError("A related activity or session requires a subject")
        return self


__all__ = ["ChallengeTarget", "StudyChallengeWrite"]
