from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class StudyCandidate:
    """An activity candidate ranked while assembling a study plan."""

    activity_id: int
    priority: str
    deadline: datetime | None
    duration_minutes: int

    def order_key(self) -> tuple[int, datetime, int, int]:
        priority_rank = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        return (
            priority_rank.get(self.priority, 4),
            self.deadline or datetime.max.replace(tzinfo=timezone.utc),
            self.duration_minutes,
            self.activity_id,
        )


__all__ = ["StudyCandidate"]
