from collections.abc import Iterator

from app.academic_intelligence.academic_event import AcademicEvent


class AcademicJourney:
    """A simply linked, chronological account of bounded academic events."""

    def __init__(self) -> None:
        self._first: AcademicEvent | None = None
        self._last: AcademicEvent | None = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def append(self, event: AcademicEvent) -> None:
        if event.following is not None:
            raise ValueError("Event is already linked")
        if self._last and event.occurred_at < self._last.occurred_at:
            raise ValueError("Academic events must be chronological")
        if self._last is None:
            self._first = event
        else:
            self._last.following = event
        self._last = event
        self._size += 1

    def __iter__(self) -> Iterator[AcademicEvent]:
        current = self._first
        while current is not None:
            yield current
            current = current.following


__all__ = ["AcademicJourney"]
