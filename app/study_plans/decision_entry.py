from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class DecisionEntry:
    """A user's recorded decision for one Plan proposal value."""

    id: int
    action: str
    field_path: str | None
    proposed_value: Any
    chosen_value: Any
    created_at: datetime


__all__ = ["DecisionEntry"]
