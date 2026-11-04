from dataclasses import dataclass


@dataclass(slots=True)
class RhythmDay:
    weekday: int
    planned_minutes: int = 0
    previous: "RhythmDay | None" = None
    next: "RhythmDay | None" = None


__all__ = ["RhythmDay"]
