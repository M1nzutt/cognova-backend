from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ScheduleEntry:
    """A dated academic resource and its AVL position."""

    at: datetime
    kind: str
    resource_id: int
    subject_id: int | None
    earlier: "ScheduleEntry | None" = None
    later: "ScheduleEntry | None" = None
    height: int = 1

    @property
    def key(self) -> tuple[datetime, str, int]:
        return self.at, self.kind, self.resource_id


__all__ = ["ScheduleEntry"]
