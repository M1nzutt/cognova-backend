from dataclasses import dataclass

from app.study_plans.decision_entry import DecisionEntry


@dataclass(slots=True)
class DecisionPassage:
    """A bidirectional position in a user's recorded decision sequence."""

    decision: DecisionEntry
    previous: "DecisionPassage | None" = None
    following: "DecisionPassage | None" = None


__all__ = ["DecisionPassage"]
