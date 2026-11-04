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
        undone_ids: set[int] = set()
        for entry in self._entries:
            if not entry.field_path or not entry.field_path.startswith("undo:"):
                continue
            parts = entry.field_path.split(":", maxsplit=2)
            if len(parts) == 3 and parts[1].isdigit():
                undone_ids.add(int(parts[1]))
        for entry in reversed(self._entries):
            if (
                entry.action == "edited"
                and entry.field_path
                and not entry.field_path.startswith("undo:")
                and entry.id not in undone_ids
            ):
                return entry
        return None


__all__ = ["DecisionHistory"]
