from app.academic_intelligence.ai_plan_snapshot import AiPlanProposalSnapshot
from app.schemas.study_plan_activity_resource import StudyPlanActivityResource
from app.schemas.study_plan_decision_response import StudyPlanDecisionResponse
from app.schemas.study_plan_session_resource import StudyPlanSessionResource
from app.schemas.study_plan_subject_resource import StudyPlanSubjectResource
from app.schemas.study_plan_summary import StudyPlanSummary
from app.schemas.study_slot_candidate_response import StudySlotCandidateResponse
from app.schemas.weekly_rhythm_entry import WeeklyRhythmEntry


class StudyPlanDetail(StudyPlanSummary):
    ai_proposal_snapshot: AiPlanProposalSnapshot | None = None
    explanation: str | None = None
    reasoning_summary: str | None = None
    subjects: list[StudyPlanSubjectResource]
    activities: list[StudyPlanActivityResource]
    study_sessions: list[StudyPlanSessionResource]
    decisions: list[StudyPlanDecisionResponse]
    challenge_count: int
    hierarchy: dict[str, object]
    priority_order: list[int]
    activity_dependency_order: list[int]
    weekly_rhythm: list[WeeklyRhythmEntry]
    candidate_slots: list[StudySlotCandidateResponse]
    schedule_conflict: bool


__all__ = ["StudyPlanDetail"]
