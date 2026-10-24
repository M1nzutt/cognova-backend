from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BeforeValidator, Field

ActivityStatus = Literal[
    "pending", "in_progress", "completed", "postponed", "cancelled"
]
ActivityPriority = Literal["low", "medium", "high", "urgent"]


def iso_datetime(value: object) -> object:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or "T" not in value.upper():
        raise ValueError("Use an ISO 8601 timestamp with timezone")
    return datetime.fromisoformat(value.replace("t", "T").replace("z", "+00:00"))


Deadline = Annotated[AwareDatetime, BeforeValidator(iso_datetime)]
EntityId = Annotated[int, Field(strict=True, gt=0, le=2147483647)]
