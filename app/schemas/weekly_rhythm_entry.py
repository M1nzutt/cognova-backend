from pydantic import BaseModel


class WeeklyRhythmEntry(BaseModel):
    weekday: int
    name: str
    planned_minutes: int


__all__ = ["WeeklyRhythmEntry"]
