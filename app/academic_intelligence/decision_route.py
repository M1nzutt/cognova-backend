from app.academic_intelligence.decision_branch import DecisionBranch


class DecisionRoute:
    """Binary evaluation of proposal viability before any persistence."""

    def __init__(self) -> None:
        enough = DecisionBranch(
            "enough_context",
            if_yes=DecisionBranch("ready", outcome="propose"),
            if_no=DecisionBranch("missing_context", outcome="insufficient_evidence"),
        )
        no_context = DecisionBranch("no_context", outcome="insufficient_evidence")
        safe_dates = DecisionBranch(
            "safe_dates",
            if_yes=enough,
            if_no=DecisionBranch("bad_dates", outcome="invalid_dates"),
        )
        self._first = DecisionBranch(
            "owned_resources", if_yes=safe_dates, if_no=no_context
        )

    def evaluate(
        self, *, has_resources: bool, valid_dates: bool, enough_context: bool
    ) -> str:
        answers = {
            "owned_resources": has_resources,
            "safe_dates": valid_dates,
            "enough_context": enough_context,
        }
        current = self._first
        while current.outcome is None:
            current = current.if_yes if answers[current.condition] else current.if_no  # type: ignore[assignment]
            assert current is not None
        return current.outcome


__all__ = ["DecisionRoute"]
