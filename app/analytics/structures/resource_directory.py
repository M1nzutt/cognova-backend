"""Request-scoped open-addressing directory for owned resources."""

from app.analytics.structures.analytics_resource import AnalyticsResource


class ResourceEntry:
    __slots__ = ("key", "value", "hash_value")

    def __init__(self, value: AnalyticsResource, hash_value: int) -> None:
        self.key = value.key
        self.value = value
        self.hash_value = hash_value


_REMOVED = object()


class ResourceDirectory:
    """Maps ``(resource_type, id)`` to a per-user response projection."""

    _INITIAL_CAPACITY = 16
    _MAX_LOAD = 0.65

    def __init__(self) -> None:
        self._slots: list[ResourceEntry | object | None] = [
            None
        ] * self._INITIAL_CAPACITY
        self._size = 0
        self._removed = 0

    def __len__(self) -> int:
        return self._size

    @staticmethod
    def _hash(key: tuple[str, int]) -> int:
        value = 2_166_136_261
        for byte in f"{key[0]}:{key[1]}".encode("utf-8"):
            value = ((value ^ byte) * 16_777_619) & 0xFFFFFFFF
        return value

    def _slot(self, key: tuple[str, int], hash_value: int) -> tuple[int, bool]:
        index = hash_value % len(self._slots)
        first_removed: int | None = None
        while True:
            entry = self._slots[index]
            if entry is None:
                return (first_removed if first_removed is not None else index), False
            if entry is _REMOVED:
                if first_removed is None:
                    first_removed = index
            elif isinstance(entry, ResourceEntry):
                if entry.hash_value == hash_value and entry.key == key:
                    return index, True
            index = (index + 1) % len(self._slots)

    def put(self, value: AnalyticsResource) -> None:
        if not value.resource_type or value.resource_id <= 0 or not value.title.strip():
            raise ValueError("Resource requires a type, positive ID, and title")
        hash_value = self._hash(value.key)
        index, found = self._slot(value.key, hash_value)
        if found:
            self._slots[index] = ResourceEntry(value, hash_value)
            return
        if (self._size + self._removed + 1) / len(self._slots) > self._MAX_LOAD:
            self._resize(len(self._slots) * 2)
            index, found = self._slot(value.key, hash_value)
            assert not found
        if self._slots[index] is _REMOVED:
            self._removed -= 1
        self._slots[index] = ResourceEntry(value, hash_value)
        self._size += 1

    def get(self, key: tuple[str, int]) -> AnalyticsResource | None:
        index, found = self._slot(key, self._hash(key))
        entry = self._slots[index]
        return entry.value if found and isinstance(entry, ResourceEntry) else None

    def remove(self, key: tuple[str, int]) -> bool:
        index, found = self._slot(key, self._hash(key))
        if not found:
            return False
        self._slots[index] = _REMOVED
        self._size -= 1
        self._removed += 1
        return True

    def values(self) -> list[AnalyticsResource]:
        return [
            entry.value for entry in self._slots if isinstance(entry, ResourceEntry)
        ]

    def _resize(self, capacity: int) -> None:
        old_values = self.values()
        self._slots = [None] * capacity
        self._size = 0
        self._removed = 0
        for value in old_values:
            hash_value = self._hash(value.key)
            index, found = self._slot(value.key, hash_value)
            assert not found
            self._slots[index] = ResourceEntry(value, hash_value)
            self._size += 1


__all__ = ["ResourceDirectory"]
