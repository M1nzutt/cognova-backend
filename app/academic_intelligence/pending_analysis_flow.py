from app.academic_intelligence.pending_analysis import PendingAnalysis


class PendingAnalysisFlow:
    """A manually linked FIFO for evidence candidates in one request."""

    def __init__(self) -> None:
        self._first: PendingAnalysis | None = None
        self._last: PendingAnalysis | None = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def add(self, item: PendingAnalysis) -> None:
        if item.following is not None:
            raise ValueError("Candidate is already linked")
        if self._last is None:
            self._first = item
        else:
            self._last.following = item
        self._last = item
        self._size += 1

    def take(self) -> PendingAnalysis | None:
        item = self._first
        if item is None:
            return None
        self._first = item.following
        if self._first is None:
            self._last = None
        item.following = None
        self._size -= 1
        return item


__all__ = ["PendingAnalysisFlow"]
