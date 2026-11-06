from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class AcademicEvent:
    """One user-owned academic event in chronological context."""

    occurred_at: datetime
    kind: str
    resource_id: int
    subject_id: int | None
    following: "AcademicEvent | None" = None


__all__ = ["AcademicEvent"]
