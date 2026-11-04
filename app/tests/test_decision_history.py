from datetime import datetime, timezone

from app.study_plans.decision_entry import DecisionEntry
from app.study_plans.decision_history import DecisionHistory


def test_decision_history_returns_recent_proposal_edit_first():
    first = DecisionEntry(
        1, "edited", "name", "Original", "Draft", datetime.now(timezone.utc)
    )
    second = DecisionEntry(
        2,
        "edited",
        "objective",
        "Learn",
        "Prepare for exam",
        datetime.now(timezone.utc),
    )
    history = DecisionHistory([first, second])

    assert history.latest() == second
    assert history.undo_latest() == second
    history.record(
        DecisionEntry(
            3,
            "edited",
            f"undo:{second.id}:{second.field_path}",
            second.chosen_value,
            second.proposed_value,
            datetime.now(timezone.utc),
        )
    )
    assert history.undo_latest() == first
    history.record(
        DecisionEntry(
            4,
            "edited",
            f"undo:{first.id}:{first.field_path}",
            first.chosen_value,
            first.proposed_value,
            datetime.now(timezone.utc),
        )
    )
    assert history.undo_latest() is None
    assert len(history) == 4
