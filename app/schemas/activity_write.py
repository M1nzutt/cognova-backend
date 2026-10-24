import unicodedata
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from app.activities.types import ActivityPriority, ActivityStatus, Deadline, EntityId


def normalize_title(value: object) -> object:
    return (
        unicodedata.normalize("NFC", value).strip() if isinstance(value, str) else value
    )


class ActivityWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Annotated[
        str, BeforeValidator(normalize_title), Field(min_length=1, max_length=50)
    ]
    subject_id: EntityId
    deadline: Deadline
    priority: ActivityPriority
    status: ActivityStatus
    estimated_duration: Annotated[int, Field(strict=True, ge=10, le=300)]
    notes: Annotated[str | None, Field(max_length=200)] = None

    @field_validator("title")
    @classmethod
    def title_controls(cls, value: str) -> str:
        if any(unicodedata.category(c).startswith("C") for c in value):
            raise ValueError("Control characters are not allowed")
        return value

    @field_validator("notes")
    @classmethod
    def notes_controls(cls, value: str | None) -> str | None:
        if value and any(
            unicodedata.category(c) in {"Cc", "Cs"} and c not in "\n\r\t" for c in value
        ):
            raise ValueError("Invalid control characters")
        return value
