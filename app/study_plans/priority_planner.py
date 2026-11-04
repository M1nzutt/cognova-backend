from app.study_plans.study_candidate import StudyCandidate


class PriorityPlanner:
    """Manually maintains plan candidates by priority, deadline, then duration."""

    def __init__(self) -> None:
        self._candidates: list[StudyCandidate] = []

    def __len__(self) -> int:
        return len(self._candidates)

    def add(self, candidate: StudyCandidate) -> None:
        self._candidates.append(candidate)
        child = len(self._candidates) - 1
        while child > 0:
            parent = (child - 1) // 2
            if self._before(self._candidates[parent], self._candidates[child]):
                break
            self._candidates[parent], self._candidates[child] = (
                self._candidates[child],
                self._candidates[parent],
            )
            child = parent

    def pop_next(self) -> StudyCandidate | None:
        if not self._candidates:
            return None
        first = self._candidates[0]
        last = self._candidates.pop()
        if self._candidates:
            self._candidates[0] = last
            parent = 0
            while True:
                left = parent * 2 + 1
                right = left + 1
                earliest = parent
                if left < len(self._candidates) and self._before(
                    self._candidates[left], self._candidates[earliest]
                ):
                    earliest = left
                if right < len(self._candidates) and self._before(
                    self._candidates[right], self._candidates[earliest]
                ):
                    earliest = right
                if earliest == parent:
                    break
                self._candidates[parent], self._candidates[earliest] = (
                    self._candidates[earliest],
                    self._candidates[parent],
                )
                parent = earliest
        return first

    def ordered(self) -> list[StudyCandidate]:
        pending = PriorityPlanner()
        pending._candidates = list(self._candidates)
        ordered: list[StudyCandidate] = []
        while candidate := pending.pop_next():
            ordered.append(candidate)
        return ordered

    @staticmethod
    def _before(left: StudyCandidate, right: StudyCandidate) -> bool:
        return left.order_key() < right.order_key()


__all__ = ["PriorityPlanner"]
