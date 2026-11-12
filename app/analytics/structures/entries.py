"""Small immutable records shared by the request-scoped analytics indexes."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    occurred_at: datetime
    category: str
    resource_type: str
    resource_id: int
    occurrence_id: int
    event_type: str
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> tuple[datetime, int, int, int, str]:
        rank = {
            "activity": 0,
            "study_session": 1,
            "decision": 2,
            "plan": 3,
            "challenge": 4,
        }.get(self.category)
        if rank is None:
            raise ValueError("Unknown analytics event category")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("Analytics event timestamps must include a UTC offset")
        if self.resource_id <= 0 or self.occurrence_id < 0:
            raise ValueError("Analytics event identifiers must be nonnegative")
        return (
            self.occurred_at,
            rank,
            self.resource_id,
            self.occurrence_id,
            self.event_type,
        )
__all__ = ["TimelineEvent"]
