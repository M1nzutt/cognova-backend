from collections.abc import Iterator

from app.academic_intelligence.decision_passage import DecisionPassage
from app.study_plans.decision_entry import DecisionEntry


class DecisionTrail:
    """A doubly linked trail of user decisions for forward/backward context."""

    def __init__(self) -> None:
        self._first: DecisionPassage | None = None
        self._last: DecisionPassage | None = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def record(self, decision: DecisionEntry) -> None:
        passage = DecisionPassage(decision, previous=self._last)
        if self._last is None:
            self._first = passage
        else:
            self._last.following = passage
        self._last = passage
        self._size += 1

    def forward(self) -> Iterator[DecisionEntry]:
        current = self._first
        while current is not None:
            yield current.decision
            current = current.following

    def backward(self) -> Iterator[DecisionEntry]:
        current = self._last
        while current is not None:
            yield current.decision
            current = current.previous


__all__ = ["DecisionTrail"]
