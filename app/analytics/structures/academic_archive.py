"""Historical timeline index implemented as a bounded-node B-tree."""

from collections.abc import Iterator
from datetime import datetime

from app.analytics.structures.entries import TimelineEvent


class ArchiveEntry:
    __slots__ = ("keys", "children", "leaf")

    def __init__(self, leaf: bool = True) -> None:
        self.keys: list[TimelineEvent] = []
        self.children: list[ArchiveEntry] = []
        self.leaf = leaf


class AcademicArchive:
    """Maintains historical events in key order with O(log E) insertion."""

    _MIN_DEGREE = 8

    def __init__(self) -> None:
        self._root = ArchiveEntry()
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def add(self, event: TimelineEvent) -> None:
        if len(self._root.keys) == 2 * self._MIN_DEGREE - 1:
            replacement = ArchiveEntry(leaf=False)
            replacement.children.append(self._root)
            self._split_child(replacement, 0)
            self._root = replacement
        self._insert_non_full(self._root, event)
        self._size += 1

    @classmethod
    def _split_child(cls, parent: ArchiveEntry, index: int) -> None:
        degree = cls._MIN_DEGREE
        full = parent.children[index]
        right = ArchiveEntry(leaf=full.leaf)
        median = full.keys[degree - 1]
        right.keys = full.keys[degree:]
        full.keys = full.keys[: degree - 1]
        if not full.leaf:
            right.children = full.children[degree:]
            full.children = full.children[:degree]
        parent.children.insert(index + 1, right)
        parent.keys.insert(index, median)

    @classmethod
    def _insert_non_full(cls, entry: ArchiveEntry, event: TimelineEvent) -> None:
        if entry.leaf:
            index = len(entry.keys)
            while index > 0 and event.key < entry.keys[index - 1].key:
                index -= 1
            if index > 0 and entry.keys[index - 1].key == event.key:
                raise ValueError("Duplicate archive event key")
            entry.keys.insert(index, event)
            return
        index = len(entry.keys) - 1
        while index >= 0 and event.key < entry.keys[index].key:
            index -= 1
        if index >= 0 and entry.keys[index].key == event.key:
            raise ValueError("Duplicate archive event key")
        index += 1
        if len(entry.children[index].keys) == 2 * cls._MIN_DEGREE - 1:
            cls._split_child(entry, index)
            if event.key == entry.keys[index].key:
                raise ValueError("Duplicate archive event key")
            if event.key > entry.keys[index].key:
                index += 1
        cls._insert_non_full(entry.children[index], event)

    def iter_range(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        after_key: tuple[datetime, int, int, int, str] | None = None,
        limit: int | None = None,
    ) -> Iterator[TimelineEvent]:
        """Yield events in timestamp range [start, end), ordered by full key."""
        if start is not None and end is not None and end <= start:
            raise ValueError("Invalid archive time range")
        lower = after_key
        if start is not None:
            start_bound = (start, -1, -1, -1, "")
            lower = max(lower, start_bound) if lower is not None else start_bound
        upper = (end, -1, -1, -1, "") if end is not None else None
        emitted = 0
        for event in self._walk_bounded(self._root, lower, upper, None, None):
            yield event
            emitted += 1
            if limit is not None and emitted >= limit:
                return

    @classmethod
    def _walk_bounded(
        cls,
        entry: ArchiveEntry,
        lower: tuple[datetime, int, int, int, str] | None,
        upper: tuple[datetime, int, int, int, str] | None,
        ancestor_lower: tuple[datetime, int, int, int, str] | None,
        ancestor_upper: tuple[datetime, int, int, int, str] | None,
    ) -> Iterator[TimelineEvent]:
        for index, event in enumerate(entry.keys):
            child_lower = ancestor_lower if index == 0 else entry.keys[index - 1].key
            child_upper = event.key
            intersects = (lower is None or child_upper > lower) and (
                upper is None or child_lower is None or child_lower < upper
            )
            if not entry.leaf and intersects:
                yield from cls._walk_bounded(
                    entry.children[index],
                    lower,
                    upper,
                    child_lower,
                    child_upper,
                )
            if lower is not None and event.key <= lower:
                continue
            if upper is not None and event.key >= upper:
                return
            yield event
        if not entry.leaf:
            child_lower = entry.keys[-1].key if entry.keys else ancestor_lower
            intersects = (
                upper is None or child_lower is None or child_lower < upper
            ) and (lower is None or ancestor_upper is None or ancestor_upper > lower)
            if intersects:
                yield from cls._walk_bounded(
                    entry.children[-1],
                    lower,
                    upper,
                    child_lower,
                    ancestor_upper,
                )

    def validate_invariants(self) -> bool:
        leaf_depths: set[int] = set()

        def check(
            entry: ArchiveEntry,
            depth: int,
            lower: tuple[datetime, int, int, int, str] | None,
            upper: tuple[datetime, int, int, int, str] | None,
            is_root: bool,
        ) -> int:
            keys = [event.key for event in entry.keys]
            if keys != sorted(keys):
                raise AssertionError("B-tree keys are not sorted")
            if len(keys) > 2 * self._MIN_DEGREE - 1:
                raise AssertionError("B-tree entry exceeds maximum key count")
            if not is_root and len(keys) < self._MIN_DEGREE - 1:
                raise AssertionError("B-tree entry is below minimum key count")
            if any(
                (lower is not None and key <= lower)
                or (upper is not None and key >= upper)
                for key in keys
            ):
                raise AssertionError("B-tree key violates ancestor bounds")
            if entry.leaf:
                if entry.children:
                    raise AssertionError("B-tree leaf has children")
                leaf_depths.add(depth)
                return len(keys)
            if len(entry.children) != len(keys) + 1:
                raise AssertionError("B-tree child/key count is inconsistent")
            count = len(keys)
            for index, child in enumerate(entry.children):
                child_lower = lower if index == 0 else keys[index - 1]
                child_upper = upper if index == len(keys) else keys[index]
                count += check(child, depth + 1, child_lower, child_upper, False)
            return count

        count = check(self._root, 0, None, None, True)
        if count != self._size or len(leaf_depths) > 1:
            raise AssertionError("B-tree size or leaf depth invariant failed")
        return True


__all__ = ["AcademicArchive"]
