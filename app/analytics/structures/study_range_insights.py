"""Exact range totals over closed study intervals using a segment tree."""

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timezone

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _microseconds(value: datetime) -> int:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Study interval timestamps must include a UTC offset")
    delta = value.astimezone(timezone.utc) - _EPOCH
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


@dataclass(frozen=True, slots=True)
class StudyInterval:
    session_id: int
    subject_id: int
    started_at: datetime
    ended_at: datetime


@dataclass(frozen=True, slots=True)
class StudyRangeTotal:
    duration_microseconds: int
    session_count: int


class _SubjectCoverage:
    def __init__(self, intervals: list[tuple[int, int, int]]) -> None:
        changes: dict[int, int] = {}
        for _, start, end in intervals:
            changes[start] = changes.get(start, 0) + 1
            changes[end] = changes.get(end, 0) - 1
        self.coordinates = sorted(changes)
        self.coverage: list[int] = []
        active = 0
        leaves: list[int] = []
        for index, point in enumerate(self.coordinates[:-1]):
            active += changes[point]
            self.coverage.append(active)
            leaves.append(active * (self.coordinates[index + 1] - point))
        self._tree_size = 1
        while self._tree_size < len(leaves):
            self._tree_size *= 2
        self._tree = [0] * (2 * self._tree_size)
        self._tree[self._tree_size : self._tree_size + len(leaves)] = leaves
        for index in range(self._tree_size - 1, 0, -1):
            self._tree[index] = self._tree[index * 2] + self._tree[index * 2 + 1]
        self.intervals = intervals

    def _sum(self, start: int, end: int) -> int:
        left = start + self._tree_size
        right = end + self._tree_size
        result = 0
        while left < right:
            if left & 1:
                result += self._tree[left]
                left += 1
            if right & 1:
                right -= 1
                result += self._tree[right]
            left //= 2
            right //= 2
        return result

    def _integral(self, point: int) -> int:
        if not self.coordinates or point <= self.coordinates[0]:
            return 0
        if point >= self.coordinates[-1]:
            return self._tree[1]
        segment = bisect_right(self.coordinates, point) - 1
        complete = self._sum(0, segment)
        return complete + (point - self.coordinates[segment]) * self.coverage[segment]

    def query(self, start: int, end: int) -> StudyRangeTotal:
        if not self.coordinates or end <= start:
            return StudyRangeTotal(0, 0)
        duration = self._integral(end) - self._integral(start)
        sessions = {
            session_id
            for session_id, interval_start, interval_end in self.intervals
            if interval_start < end and interval_end > start
        }
        return StudyRangeTotal(duration, len(sessions))


class StudyRangeInsights:
    """Answers clipped interval totals with weighted segment-tree range sums.

    Construction is O(S log S) across S closed interval endpoints. Each range
    duration query is O(log S) per subject; distinct-session counts scan that
    subject's intervals, O(S) in the current implementation.
    """

    def __init__(self, intervals: list[StudyInterval] | None = None) -> None:
        self._by_subject: dict[int, _SubjectCoverage] = {}
        grouped: dict[int, list[tuple[int, int, int]]] = {}
        for interval in intervals or []:
            if interval.session_id <= 0 or interval.subject_id <= 0:
                raise ValueError("Session and subject IDs must be positive")
            start = _microseconds(interval.started_at)
            end = _microseconds(interval.ended_at)
            if end <= start:
                raise ValueError("Study intervals must have positive duration")
            grouped.setdefault(interval.subject_id, []).append(
                (interval.session_id, start, end)
            )
        self._by_subject = {
            subject_id: _SubjectCoverage(subject_intervals)
            for subject_id, subject_intervals in grouped.items()
        }

    def between(self, start: datetime, end: datetime) -> dict[int, StudyRangeTotal]:
        """Return per-subject totals clipped to the half-open range [start, end)."""
        start_us = _microseconds(start)
        end_us = _microseconds(end)
        if end_us <= start_us:
            raise ValueError("Study range end must be after start")
        return {
            subject_id: coverage.query(start_us, end_us)
            for subject_id, coverage in sorted(self._by_subject.items())
        }


__all__ = ["StudyInterval", "StudyRangeInsights", "StudyRangeTotal"]
