from collections.abc import Iterator
from datetime import datetime

from app.academic_intelligence.schedule_entry import ScheduleEntry


class ScheduleIndex:
    """AVL index for bounded sessions and activity deadlines in one request."""

    def __init__(self) -> None:
        self._root: ScheduleEntry | None = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    @staticmethod
    def _height(entry: ScheduleEntry | None) -> int:
        return entry.height if entry else 0

    @classmethod
    def _refresh(cls, entry: ScheduleEntry) -> None:
        entry.height = 1 + max(cls._height(entry.earlier), cls._height(entry.later))

    @classmethod
    def _rotate_later(cls, entry: ScheduleEntry) -> ScheduleEntry:
        next_entry = entry.later
        assert next_entry is not None
        entry.later = next_entry.earlier
        next_entry.earlier = entry
        cls._refresh(entry)
        cls._refresh(next_entry)
        return next_entry

    @classmethod
    def _rotate_earlier(cls, entry: ScheduleEntry) -> ScheduleEntry:
        next_entry = entry.earlier
        assert next_entry is not None
        entry.earlier = next_entry.later
        next_entry.later = entry
        cls._refresh(entry)
        cls._refresh(next_entry)
        return next_entry

    @classmethod
    def _balance(cls, entry: ScheduleEntry) -> ScheduleEntry:
        cls._refresh(entry)
        tilt = cls._height(entry.earlier) - cls._height(entry.later)
        if tilt > 1:
            assert entry.earlier is not None
            if cls._height(entry.earlier.earlier) < cls._height(entry.earlier.later):
                entry.earlier = cls._rotate_later(entry.earlier)
            return cls._rotate_earlier(entry)
        if tilt < -1:
            assert entry.later is not None
            if cls._height(entry.later.later) < cls._height(entry.later.earlier):
                entry.later = cls._rotate_earlier(entry.later)
            return cls._rotate_later(entry)
        return entry

    @classmethod
    def _insert(cls, root: ScheduleEntry | None, entry: ScheduleEntry) -> ScheduleEntry:
        if root is None:
            return entry
        if entry.key < root.key:
            root.earlier = cls._insert(root.earlier, entry)
        elif entry.key > root.key:
            root.later = cls._insert(root.later, entry)
        else:
            raise ValueError("Duplicate schedule entry")
        return cls._balance(root)

    def add(self, entry: ScheduleEntry) -> None:
        if entry.earlier or entry.later or entry.height != 1:
            raise ValueError("Schedule entry already indexed")
        self._root = self._insert(self._root, entry)
        self._size += 1

    def between(self, start: datetime, end: datetime) -> Iterator[ScheduleEntry]:
        """Return entries in the half-open interval [start, end), sorted by key."""
        if end <= start:
            raise ValueError("Invalid schedule range")
        yield from self._between(self._root, start, end)

    @classmethod
    def _between(
        cls, root: ScheduleEntry | None, start: datetime, end: datetime
    ) -> Iterator[ScheduleEntry]:
        if root is None:
            return
        if root.at >= start:
            yield from cls._between(root.earlier, start, end)
        if start <= root.at < end:
            yield root
        if root.at < end:
            yield from cls._between(root.later, start, end)

    def max_depth(self) -> int:
        return self._height(self._root)


__all__ = ["ScheduleIndex"]
