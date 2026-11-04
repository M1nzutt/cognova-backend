from datetime import datetime, timedelta

from app.study_plans.schedule_entry import ScheduleEntry


class StudySlots:
    """Fixed-capacity array of plan sessions with manual gap discovery."""

    def __init__(self, capacity: int = 500) -> None:
        if capacity <= 0:
            raise ValueError("Study slot capacity must be positive")
        self._entries: list[ScheduleEntry | None] = [None] * capacity
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def reserve(self, entry: ScheduleEntry) -> None:
        if entry.end_at <= entry.start_at:
            raise ValueError("Study slot must end after it starts")
        if self._size == len(self._entries):
            raise OverflowError("Study slot capacity exceeded")
        insert_at = 0
        while insert_at < self._size:
            current = self._entries[insert_at]
            assert current is not None
            if entry.start_at < current.start_at:
                break
            if entry.start_at < current.end_at and entry.end_at > current.start_at:
                raise ValueError("Study slot overlaps an existing session")
            insert_at += 1
        if insert_at > 0:
            previous = self._entries[insert_at - 1]
            assert previous is not None
            if entry.start_at < previous.end_at:
                raise ValueError("Study slot overlaps an existing session")
        following = self._entries[insert_at] if insert_at < self._size else None
        if following is not None and entry.end_at > following.start_at:
            raise ValueError("Study slot overlaps an existing session")
        for index in range(self._size, insert_at, -1):
            self._entries[index] = self._entries[index - 1]
        self._entries[insert_at] = entry
        self._size += 1

    def available_slots(
        self, start_at: datetime, end_at: datetime, duration_minutes: int
    ) -> list[ScheduleEntry]:
        if end_at <= start_at or duration_minutes <= 0:
            raise ValueError("A valid range and positive duration are required")
        duration = timedelta(minutes=duration_minutes)
        cursor = start_at
        available: list[ScheduleEntry] = []
        for index in range(self._size):
            current = self._entries[index]
            assert current is not None
            if current.end_at <= cursor or current.start_at >= end_at:
                continue
            gap_end = min(current.start_at, end_at)
            if gap_end - cursor >= duration:
                available.append(
                    ScheduleEntry(cursor, cursor + duration, None, "candidate")
                )
            cursor = max(cursor, current.end_at)
            if cursor >= end_at:
                break
        if end_at - cursor >= duration:
            available.append(ScheduleEntry(cursor, cursor + duration, None, "candidate"))
        return available

    def entries(self) -> list[ScheduleEntry]:
        return [
            entry
            for entry in self._entries[: self._size]
            if entry is not None
        ]


__all__ = ["StudySlots"]
