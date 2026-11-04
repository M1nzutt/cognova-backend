from datetime import datetime

from app.study_plans.rhythm_day import RhythmDay


class WeeklyRhythm:
    """Circular, doubly linked weekly totals for planned study time."""

    _names = (
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )

    def __init__(self) -> None:
        self._days = [RhythmDay(weekday) for weekday in range(7)]
        for weekday, day in enumerate(self._days):
            day.previous = self._days[(weekday - 1) % 7]
            day.next = self._days[(weekday + 1) % 7]

    def add_session(self, planned_start_at: datetime, duration_minutes: int) -> None:
        if duration_minutes <= 0:
            raise ValueError("Study duration must be positive")
        self._days[planned_start_at.weekday()].planned_minutes += duration_minutes

    def next_day(self, weekday: int) -> RhythmDay:
        self._validate_weekday(weekday)
        day = self._days[weekday].next
        assert day is not None
        return day

    def previous_day(self, weekday: int) -> RhythmDay:
        self._validate_weekday(weekday)
        day = self._days[weekday].previous
        assert day is not None
        return day

    def totals(self, start_weekday: int = 0) -> list[dict[str, int | str]]:
        self._validate_weekday(start_weekday)
        day = self._days[start_weekday]
        totals: list[dict[str, int | str]] = []
        for _ in range(7):
            totals.append(
                {
                    "weekday": day.weekday,
                    "name": self._names[day.weekday],
                    "planned_minutes": day.planned_minutes,
                }
            )
            assert day.next is not None
            day = day.next
        return totals

    @staticmethod
    def _validate_weekday(weekday: int) -> None:
        if weekday not in range(7):
            raise ValueError("Weekday must be between 0 and 6")


__all__ = ["WeeklyRhythm"]
