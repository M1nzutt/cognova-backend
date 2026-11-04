from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ScheduleEntry:
    """A reserved session interval or a candidate interval in a Plan."""

    start_at: datetime
    end_at: datetime
    reference_id: int | None
    kind: str


__all__ = ["ScheduleEntry"]
