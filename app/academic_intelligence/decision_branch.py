from dataclasses import dataclass


@dataclass(slots=True)
class DecisionBranch:
    """One domain question in proposal viability evaluation."""

    condition: str
    if_yes: "DecisionBranch | None" = None
    if_no: "DecisionBranch | None" = None
    outcome: str | None = None


__all__ = ["DecisionBranch"]
