from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.domain_error import DomainError
from app.models.activity import Activity
from app.models.study_plans import (
    StudyChallenge,
    StudyPlan,
    StudyPlanActivity,
    StudyPlanDecision,
    StudyPlanSession,
    StudyPlanSubject,
)
from app.models.study_session import StudySession
from app.models.subject import Subject
from app.schemas.study_plan_activity_resource import StudyPlanActivityResource
from app.schemas.study_plan_decision_response import StudyPlanDecisionResponse
from app.schemas.study_plan_detail import StudyPlanDetail
from app.schemas.study_plan_session_resource import StudyPlanSessionResource
from app.schemas.study_plan_subject_resource import StudyPlanSubjectResource
from app.schemas.study_plan_summary import StudyPlanSummary
from app.schemas.study_slot_candidate_response import StudySlotCandidateResponse
from app.schemas.weekly_rhythm_entry import WeeklyRhythmEntry
from app.study_plans.dependency_network import DependencyNetwork
from app.study_plans.learning_plan_map import LearningPlanMap
from app.study_plans.priority_planner import PriorityPlanner
from app.study_plans.schedule_entry import ScheduleEntry
from app.study_plans.study_candidate import StudyCandidate
from app.study_plans.study_slots import StudySlots
from app.study_plans.weekly_rhythm import WeeklyRhythm


class StudyPlanProjection:
    """Builds a Plan view from owned records without duplicating persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def detail(self, plan: StudyPlan) -> StudyPlanDetail:
        subjects = self._subjects(plan)
        activities = self._activities(plan)
        sessions = self._sessions(plan)
        challenges = self._challenges(plan)
        decisions = self._decisions(plan)
        hierarchy = self._hierarchy(plan, subjects, activities, sessions, challenges)
        priority_order = self._priority_order(activities)
        activity_dependency_order = self._dependency_order(activities, challenges)
        weekly_rhythm = self._weekly_rhythm(sessions)
        candidate_slots, schedule_conflict = self._candidate_slots(plan, sessions)

        return StudyPlanDetail(
            **StudyPlanSummary.model_validate(plan).model_dump(),
            subjects=[
                StudyPlanSubjectResource(id=row.id, name=row.name) for row in subjects
            ],
            activities=[
                StudyPlanActivityResource.model_validate(row) for row in activities
            ],
            study_sessions=[
                StudyPlanSessionResource.model_validate(row) for row in sessions
            ],
            decisions=[
                StudyPlanDecisionResponse.model_validate(row) for row in decisions
            ],
            challenge_count=len(challenges),
            hierarchy=hierarchy.as_dict(),
            priority_order=priority_order,
            activity_dependency_order=activity_dependency_order,
            weekly_rhythm=[WeeklyRhythmEntry(**entry) for entry in weekly_rhythm],
            candidate_slots=[
                StudySlotCandidateResponse(
                    start_at=entry.start_at,
                    end_at=entry.end_at,
                    duration_minutes=int(
                        (entry.end_at - entry.start_at).total_seconds() // 60
                    ),
                )
                for entry in candidate_slots
            ],
            schedule_conflict=schedule_conflict,
        )

    def _subjects(self, plan: StudyPlan) -> list[Subject]:
        ids = self._db.scalars(
            select(StudyPlanSubject.subject_id)
            .where(
                StudyPlanSubject.user_id == plan.user_id,
                StudyPlanSubject.plan_id == plan.id,
            )
            .order_by(StudyPlanSubject.subject_id)
        ).all()
        if not ids:
            return []
        return list(
            self._db.scalars(
                select(Subject)
                .where(Subject.user_id == plan.user_id, Subject.id.in_(ids))
                .order_by(Subject.id)
            ).all()
        )

    def _activities(self, plan: StudyPlan) -> list[Activity]:
        ids = self._db.scalars(
            select(StudyPlanActivity.activity_id)
            .where(
                StudyPlanActivity.user_id == plan.user_id,
                StudyPlanActivity.plan_id == plan.id,
            )
            .order_by(StudyPlanActivity.activity_id)
        ).all()
        if not ids:
            return []
        return list(
            self._db.scalars(
                select(Activity)
                .where(Activity.user_id == plan.user_id, Activity.id.in_(ids))
                .order_by(Activity.id)
            ).all()
        )

    def _sessions(self, plan: StudyPlan) -> list[StudySession]:
        ids = self._db.scalars(
            select(StudyPlanSession.study_session_id).where(
                StudyPlanSession.user_id == plan.user_id,
                StudyPlanSession.plan_id == plan.id,
            )
        ).all()
        if not ids:
            return []
        return list(
            self._db.scalars(
                select(StudySession)
                .where(StudySession.user_id == plan.user_id, StudySession.id.in_(ids))
                .order_by(StudySession.planned_start_at, StudySession.id)
            ).all()
        )

    def _challenges(self, plan: StudyPlan) -> list[StudyChallenge]:
        return list(
            self._db.scalars(
                select(StudyChallenge)
                .where(
                    StudyChallenge.user_id == plan.user_id,
                    StudyChallenge.plan_id == plan.id,
                )
                .order_by(StudyChallenge.id)
            ).all()
        )

    def _decisions(self, plan: StudyPlan) -> list[StudyPlanDecision]:
        return list(
            self._db.scalars(
                select(StudyPlanDecision)
                .where(
                    StudyPlanDecision.user_id == plan.user_id,
                    StudyPlanDecision.plan_id == plan.id,
                )
                .order_by(StudyPlanDecision.created_at, StudyPlanDecision.id)
            ).all()
        )

    @staticmethod
    def _hierarchy(
        plan: StudyPlan,
        subjects: list[Subject],
        activities: list[Activity],
        sessions: list[StudySession],
        challenges: list[StudyChallenge],
    ) -> LearningPlanMap:
        hierarchy = LearningPlanMap(plan.id, plan.name)
        activity_ids: set[int] = set()
        for subject in subjects:
            hierarchy.add(
                key=f"subject:{subject.id}",
                kind="subject",
                label=subject.name,
                parent_key=f"plan:{plan.id}",
            )
        for activity in activities:
            activity_ids.add(activity.id)
            hierarchy.add(
                key=f"activity:{activity.id}",
                kind="activity",
                label=activity.title,
                parent_key=f"subject:{activity.subject_id}",
            )
        for session in sessions:
            parent_key = (
                f"activity:{session.activity_id}"
                if session.activity_id in activity_ids
                else f"subject:{session.subject_id}"
            )
            hierarchy.add(
                key=f"session:{session.id}",
                kind="study_session",
                label=f"Sesión {session.id}",
                parent_key=parent_key,
            )
        for challenge in challenges:
            if challenge.activity_id is not None:
                parent_key = f"activity:{challenge.activity_id}"
            elif challenge.study_session_id is not None:
                parent_key = f"session:{challenge.study_session_id}"
            elif challenge.subject_id is not None:
                parent_key = f"subject:{challenge.subject_id}"
            else:
                parent_key = f"plan:{plan.id}"
            hierarchy.add(
                key=f"challenge:{challenge.id}",
                kind="challenge",
                label=challenge.title,
                parent_key=parent_key,
            )
        return hierarchy

    @staticmethod
    def _priority_order(activities: list[Activity]) -> list[int]:
        planner = PriorityPlanner()
        for activity in activities:
            planner.add(
                StudyCandidate(
                    activity.id,
                    activity.priority,
                    activity.deadline,
                    activity.estimated_duration,
                )
            )
        return [candidate.activity_id for candidate in planner.ordered()]

    @staticmethod
    def _dependency_order(
        activities: list[Activity], challenges: list[StudyChallenge]
    ) -> list[int]:
        network = DependencyNetwork()
        activity_ids = {activity.id for activity in activities}
        for activity_id in sorted(activity_ids):
            network.add_activity(activity_id)
        added: set[tuple[int, int]] = set()
        for challenge in challenges:
            target_id = challenge.activity_id
            dependencies = challenge.generation_criteria.get(
                "depends_on_activity_ids", []
            )
            if target_id is None:
                continue
            if not isinstance(dependencies, list):
                raise DomainError("STUDY_PLAN_DEPENDENCY_CONFLICT")
            for dependency_id in dependencies:
                edge = (target_id, dependency_id)
                if type(dependency_id) is not int or dependency_id not in activity_ids:
                    raise DomainError("STUDY_PLAN_DEPENDENCY_CONFLICT")
                if edge in added:
                    continue
                try:
                    network.add_dependency(target_id, dependency_id)
                except ValueError:
                    raise DomainError("STUDY_PLAN_DEPENDENCY_CONFLICT") from None
                added.add(edge)
        try:
            return network.study_order()
        except ValueError:
            raise DomainError("STUDY_PLAN_DEPENDENCY_CONFLICT") from None

    @staticmethod
    def _weekly_rhythm(sessions: list[StudySession]) -> list[dict[str, int | str]]:
        rhythm = WeeklyRhythm()
        for session in sessions:
            rhythm.add_session(session.planned_start_at, session.planned_duration)
        return rhythm.totals()

    @staticmethod
    def _candidate_slots(
        plan: StudyPlan, sessions: list[StudySession]
    ) -> tuple[list[ScheduleEntry], bool]:
        slots = StudySlots(max(1, len(sessions)))
        schedule_conflict = False
        for session in sessions:
            end_at = session.planned_start_at + timedelta(
                minutes=session.planned_duration
            )
            if session.planned_start_at < plan.start_at or end_at > plan.end_at:
                schedule_conflict = True
                break
            try:
                slots.reserve(
                    ScheduleEntry(
                        session.planned_start_at,
                        end_at,
                        session.id,
                        "study_session",
                    )
                )
            except ValueError:
                schedule_conflict = True
                break
        if schedule_conflict:
            return [], True
        return slots.available_slots(plan.start_at, plan.end_at, 30), False


__all__ = ["StudyPlanProjection"]
