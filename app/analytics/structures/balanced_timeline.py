"""Planned/current timeline index implemented as a red-black tree."""

from collections.abc import Iterator
from datetime import datetime

from app.analytics.structures.entries import TimelineEvent


class TimelineEntry:
    __slots__ = ("event", "red", "earlier", "later", "parent")

    def __init__(self, event: TimelineEvent) -> None:
        self.event = event
        self.red = True
        self.earlier: TimelineEntry | None = None
        self.later: TimelineEntry | None = None
        self.parent: TimelineEntry | None = None

    @property
    def key(self) -> tuple[datetime, int, int, int, str]:
        return self.event.key


class BalancedTimeline:
    """Indexes planned/current events with logarithmic insert and range start."""

    def __init__(self) -> None:
        self._root: TimelineEntry | None = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    @staticmethod
    def _is_red(entry: TimelineEntry | None) -> bool:
        return entry is not None and entry.red

    def add(self, event: TimelineEvent) -> None:
        inserted = TimelineEntry(event)
        parent: TimelineEntry | None = None
        current = self._root
        while current is not None:
            parent = current
            if inserted.key < current.key:
                current = current.earlier
            elif inserted.key > current.key:
                current = current.later
            else:
                raise ValueError("Duplicate timeline event key")
        inserted.parent = parent
        if parent is None:
            self._root = inserted
        elif inserted.key < parent.key:
            parent.earlier = inserted
        else:
            parent.later = inserted
        self._repair_after_insert(inserted)
        self._size += 1

    def _rotate_later(self, pivot: TimelineEntry) -> None:
        replacement = pivot.later
        assert replacement is not None
        pivot.later = replacement.earlier
        if replacement.earlier is not None:
            replacement.earlier.parent = pivot
        replacement.parent = pivot.parent
        if pivot.parent is None:
            self._root = replacement
        elif pivot is pivot.parent.earlier:
            pivot.parent.earlier = replacement
        else:
            pivot.parent.later = replacement
        replacement.earlier = pivot
        pivot.parent = replacement

    def _rotate_earlier(self, pivot: TimelineEntry) -> None:
        replacement = pivot.earlier
        assert replacement is not None
        pivot.earlier = replacement.later
        if replacement.later is not None:
            replacement.later.parent = pivot
        replacement.parent = pivot.parent
        if pivot.parent is None:
            self._root = replacement
        elif pivot is pivot.parent.later:
            pivot.parent.later = replacement
        else:
            pivot.parent.earlier = replacement
        replacement.later = pivot
        pivot.parent = replacement

    def _repair_after_insert(self, entry: TimelineEntry) -> None:
        while entry.parent is not None and entry.parent.red:
            parent = entry.parent
            grandparent = parent.parent
            assert grandparent is not None
            if parent is grandparent.earlier:
                uncle = grandparent.later
                if self._is_red(uncle):
                    parent.red = False
                    assert uncle is not None
                    uncle.red = False
                    grandparent.red = True
                    entry = grandparent
                else:
                    if entry is parent.later:
                        entry = parent
                        self._rotate_later(entry)
                        rotated_parent = entry.parent
                        assert rotated_parent is not None
                        parent = rotated_parent
                        grandparent = parent.parent
                        assert grandparent is not None
                    parent.red = False
                    grandparent.red = True
                    self._rotate_earlier(grandparent)
            else:
                uncle = grandparent.earlier
                if self._is_red(uncle):
                    parent.red = False
                    assert uncle is not None
                    uncle.red = False
                    grandparent.red = True
                    entry = grandparent
                else:
                    if entry is parent.earlier:
                        entry = parent
                        self._rotate_earlier(entry)
                        rotated_parent = entry.parent
                        assert rotated_parent is not None
                        parent = rotated_parent
                        grandparent = parent.parent
                        assert grandparent is not None
                    parent.red = False
                    grandparent.red = True
                    self._rotate_later(grandparent)
        assert self._root is not None
        self._root.red = False

    def iter_range(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        after_key: tuple[datetime, int, int, int, str] | None = None,
        limit: int | None = None,
    ) -> Iterator[TimelineEvent]:
        """Yield events in [start, end), after an optional exclusive key."""
        if start is not None and end is not None and end <= start:
            raise ValueError("Invalid timeline time range")
        lower = after_key
        if start is not None:
            start_bound = (start, -1, -1, -1, "")
            lower = max(lower, start_bound) if lower is not None else start_bound
        upper = (end, -1, -1, -1, "") if end is not None else None
        stack: list[TimelineEntry] = []
        current = self._root
        while current is not None:
            if lower is None or current.key > lower:
                stack.append(current)
                current = current.earlier
            else:
                current = current.later
        emitted = 0
        while stack:
            current = stack.pop()
            if upper is not None and current.key >= upper:
                return
            yield current.event
            emitted += 1
            if limit is not None and emitted >= limit:
                return
            current = current.later
            while current is not None:
                stack.append(current)
                current = current.earlier

    def validate_invariants(self) -> bool:
        if self._root is None:
            if self._size != 0:
                raise AssertionError("Empty red-black tree has nonzero size")
            return True
        if self._root.red or self._root.parent is not None:
            raise AssertionError("Red-black root must be black and parentless")

        def check(
            entry: TimelineEntry | None,
            lower: tuple[datetime, int, int, int, str] | None,
            upper: tuple[datetime, int, int, int, str] | None,
            parent: TimelineEntry | None,
        ) -> tuple[int, int]:
            if entry is None:
                return 1, 0
            if entry.parent is not parent:
                raise AssertionError("Red-black parent pointer mismatch")
            if (lower is not None and entry.key <= lower) or (
                upper is not None and entry.key >= upper
            ):
                raise AssertionError("Red-black key violates ancestor ordering")
            if entry.red and (self._is_red(entry.earlier) or self._is_red(entry.later)):
                raise AssertionError("Red-black tree has consecutive red entries")
            earlier_black, earlier_count = check(entry.earlier, lower, entry.key, entry)
            later_black, later_count = check(entry.later, entry.key, upper, entry)
            if earlier_black != later_black:
                raise AssertionError("Red-black paths have different black heights")
            return earlier_black + (
                0 if entry.red else 1
            ), earlier_count + later_count + 1

        _, count = check(self._root, None, None, None)
        if count != self._size:
            raise AssertionError("Red-black indexed size mismatch")
        return True


__all__ = ["BalancedTimeline"]
