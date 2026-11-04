from app.study_plans.plan_branch import PlanBranch


class LearningPlanMap:
    """Manually indexes a Plan → Subject → Activity/Session/Challenge hierarchy."""

    def __init__(self, plan_id: int, name: str) -> None:
        self.root = PlanBranch(f"plan:{plan_id}", "plan", name)
        self._branches = {self.root.key: self.root}

    def add(
        self, *, key: str, kind: str, label: str, parent_key: str
    ) -> PlanBranch:
        if key in self._branches:
            raise ValueError("Plan resource keys must be unique")
        parent = self._branches.get(parent_key)
        if parent is None:
            raise KeyError("Plan parent does not exist")
        branch = PlanBranch(key, kind, label)
        parent.children.append(branch)
        self._branches[key] = branch
        return branch

    def find(self, key: str) -> PlanBranch | None:
        return self._branches.get(key)

    def walk(self) -> list[PlanBranch]:
        ordered: list[PlanBranch] = []
        pending = [self.root]
        while pending:
            branch = pending.pop()
            ordered.append(branch)
            pending.extend(reversed(branch.children))
        return ordered

    def as_dict(self) -> dict[str, object]:
        return self.root.as_dict()


__all__ = ["LearningPlanMap"]
