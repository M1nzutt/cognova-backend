from app.study_plans.decision_entry import DecisionEntry


class DecisionHistory:
    """Stores recent proposal edits in memory with last-in-first-out access."""

    def __init__(self, entries: list[DecisionEntry] | None = None) -> None:
        self._entries = list(entries or [])

    def __len__(self) -> int:
        return len(self._entries)

    def record(self, entry: DecisionEntry) -> None:
        self._entries.append(entry)

    def latest(self) -> DecisionEntry | None:
        return self._entries[-1] if self._entries else None

    def undo_latest(self) -> DecisionEntry | None:
        if not self._entries:
            return None
        return self._entries.pop()


__all__ = ["DecisionHistory"]
