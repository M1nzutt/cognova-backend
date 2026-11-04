from datetime import datetime, timezone

from app.study_plans.priority_planner import PriorityPlanner
from app.study_plans.study_candidate import StudyCandidate


def test_priority_planner_orders_priority_deadline_and_duration():
    planner = PriorityPlanner()
    planner.add(StudyCandidate(8, "medium", None, 20))
    planner.add(
        StudyCandidate(7, "high", datetime(2030, 2, 1, tzinfo=timezone.utc), 60)
    )
    planner.add(
        StudyCandidate(6, "high", datetime(2030, 1, 1, tzinfo=timezone.utc), 40)
    )
    planner.add(
        StudyCandidate(5, "high", datetime(2030, 1, 1, tzinfo=timezone.utc), 20)
    )
    planner.add(
        StudyCandidate(4, "urgent", datetime(2030, 3, 1, tzinfo=timezone.utc), 10)
    )

    assert [candidate.activity_id for candidate in planner.ordered()] == [4, 5, 6, 7, 8]
    assert len(planner) == 5
    assert planner.pop_next().activity_id == 4
    assert len(planner) == 4


def test_priority_planner_handles_empty_and_tied_candidates_stably():
    planner = PriorityPlanner()
    assert planner.pop_next() is None
    deadline = datetime(2030, 1, 1, tzinfo=timezone.utc)
    planner.add(StudyCandidate(2, "low", deadline, 30))
    planner.add(StudyCandidate(1, "low", deadline, 30))

    assert [candidate.activity_id for candidate in planner.ordered()] == [1, 2]
