from dataclasses import dataclass, field


@dataclass(slots=True)
class PlanBranch:
    """A domain branch in a plan's resource hierarchy."""

    key: str
    kind: str
    label: str
    children: list["PlanBranch"] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "kind": self.kind,
            "label": self.label,
            "children": [child.as_dict() for child in self.children],
        }


__all__ = ["PlanBranch"]
