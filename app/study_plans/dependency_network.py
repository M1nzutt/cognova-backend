class DependencyNetwork:
    """Tracks prerequisite activities and rejects circular study plans."""

    def __init__(self) -> None:
        self._prerequisites: dict[int, list[int]] = {}
        self._dependents: dict[int, list[int]] = {}

    def add_activity(self, activity_id: int) -> None:
        if activity_id <= 0:
            raise ValueError("Activity identifiers must be positive")
        self._prerequisites.setdefault(activity_id, [])
        self._dependents.setdefault(activity_id, [])

    def add_dependency(self, activity_id: int, prerequisite_activity_id: int) -> None:
        if activity_id <= 0 or prerequisite_activity_id <= 0:
            raise ValueError("Activity identifiers must be positive")
        if activity_id == prerequisite_activity_id:
            raise ValueError("An activity cannot depend on itself")
        if self._reachable(prerequisite_activity_id, activity_id):
            raise ValueError("Activity dependencies cannot contain a cycle")
        prerequisites = self._prerequisites.setdefault(activity_id, [])
        if prerequisite_activity_id in prerequisites:
            raise ValueError("Activity dependency already exists")
        prerequisites.append(prerequisite_activity_id)
        self._prerequisites.setdefault(prerequisite_activity_id, [])
        self._dependents.setdefault(prerequisite_activity_id, []).append(activity_id)
        self._dependents.setdefault(activity_id, [])

    def prerequisites_for(self, activity_id: int) -> tuple[int, ...]:
        return tuple(self._prerequisites.get(activity_id, ()))

    def breadth_first(self, activity_id: int) -> list[int]:
        ordered: list[int] = []
        pending = [activity_id]
        visited: set[int] = set()
        cursor = 0
        while cursor < len(pending):
            current = pending[cursor]
            cursor += 1
            if current in visited:
                continue
            visited.add(current)
            ordered.append(current)
            pending.extend(self._prerequisites.get(current, ()))
        return ordered

    def depth_first(self, activity_id: int) -> list[int]:
        ordered: list[int] = []
        pending = [activity_id]
        visited: set[int] = set()
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            ordered.append(current)
            pending.extend(reversed(self._prerequisites.get(current, ())))
        return ordered

    def study_order(self) -> list[int]:
        all_activities = list(self._prerequisites)
        incoming = {activity_id: 0 for activity_id in all_activities}
        for dependents in self._dependents.values():
            for dependent in dependents:
                incoming[dependent] += 1
        ready = [activity_id for activity_id in all_activities if incoming[activity_id] == 0]
        ready.sort()
        ordered: list[int] = []
        while ready:
            prerequisite = ready.pop(0)
            ordered.append(prerequisite)
            for dependent in self._dependents.get(prerequisite, ()):
                incoming[dependent] -= 1
                if incoming[dependent] == 0:
                    ready.append(dependent)
                    ready.sort()
        if len(ordered) != len(all_activities):
            raise ValueError("Activity dependencies cannot contain a cycle")
        return ordered

    def _reachable(self, start: int, target: int) -> bool:
        pending = [start]
        visited: set[int] = set()
        while pending:
            current = pending.pop()
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)
            pending.extend(self._prerequisites.get(current, ()))
        return False


__all__ = ["DependencyNetwork"]
