"""Bounded, owner-scoped evidence for planning and observation requests."""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.academic_intelligence.academic_event import AcademicEvent
from app.academic_intelligence.academic_journey import AcademicJourney
from app.academic_intelligence.decision_trail import DecisionTrail
from app.academic_intelligence.pending_analysis import PendingAnalysis
from app.academic_intelligence.pending_analysis_flow import PendingAnalysisFlow
from app.academic_intelligence.schedule_entry import ScheduleEntry
from app.academic_intelligence.schedule_index import ScheduleIndex
from app.models.activity import Activity
from app.models.questionnaire_response import QuestionnaireResponseRecord
from app.models.study_plans import StudyChallenge, StudyPlan, StudyPlanDecision
from app.models.study_session import StudySession
from app.models.subject import Subject
from app.study_plans.decision_entry import DecisionEntry


class AcademicContext:
    def __init__(self, db: Session, user_id: int) -> None:
        self.subjects = db.scalars(
            select(Subject)
            .where(Subject.user_id == user_id)
            .order_by(Subject.id)
            .limit(100)
        ).all()
        self.activities = db.scalars(
            select(Activity)
            .where(Activity.user_id == user_id)
            .order_by(Activity.id.desc())
            .limit(200)
        ).all()
        self.sessions = db.scalars(
            select(StudySession)
            .where(StudySession.user_id == user_id)
            .order_by(StudySession.id.desc())
            .limit(200)
        ).all()
        self.plans = db.scalars(
            select(StudyPlan)
            .where(StudyPlan.user_id == user_id)
            .order_by(StudyPlan.id.desc())
            .limit(20)
        ).all()
        self.challenges = db.scalars(
            select(StudyChallenge)
            .where(StudyChallenge.user_id == user_id)
            .order_by(StudyChallenge.id.desc())
            .limit(50)
        ).all()
        self.decisions = db.scalars(
            select(StudyPlanDecision)
            .where(StudyPlanDecision.user_id == user_id)
            .order_by(StudyPlanDecision.id.desc())
            .limit(50)
        ).all()
        self.questionnaire = db.scalar(
            select(QuestionnaireResponseRecord)
            .where(QuestionnaireResponseRecord.user_id == user_id)
            .order_by(QuestionnaireResponseRecord.revision.desc())
            .limit(1)
        )
        self.finished_count = (
            db.scalar(
                select(func.count())
                .select_from(StudySession)
                .where(
                    StudySession.user_id == user_id,
                    StudySession.execution_state == "finished",
                    StudySession.status.in_(("completed", "partial")),
                    StudySession.actual_duration > 0,
                )
            )
            or 0
        )
        self.subject_ids = {row.id for row in self.subjects}
        self.activity_ids = {row.id for row in self.activities}
        self.session_ids = {row.id for row in self.sessions}
        self.evidence_catalog = {
            **{
                f"subject:{row.id}": (
                    f"Materia {row.name}: estado {row.status}; "
                    f"dificultad {row.difficulty}."
                )
                for row in self.subjects
            },
            **{
                f"activity:{row.id}": (
                    f"Actividad {row.title}: estado {row.status}; "
                    f"prioridad {row.priority}; "
                    f"fecha límite {row.deadline.isoformat()}."
                )
                for row in self.activities
            },
            **{
                f"session:{row.id}": (
                    f"Sesión {row.id}: {row.planned_duration} minutos planificados, "
                    f"{float(row.actual_duration)} reales, resultado {row.status}."
                )
                for row in self.sessions
            },
        }
        self._journey = AcademicJourney()
        self._schedule = ScheduleIndex()
        self._pending = PendingAnalysisFlow()
        self._trail = DecisionTrail()
        events = [
            AcademicEvent(row.deadline, "activity", row.id, row.subject_id)
            for row in self.activities
        ] + [
            AcademicEvent(row.planned_start_at, "study_session", row.id, row.subject_id)
            for row in self.sessions
        ]
        for event in sorted(
            events, key=lambda item: (item.occurred_at, item.kind, item.resource_id)
        ):
            self._journey.append(event)
            self._schedule.add(
                ScheduleEntry(
                    event.occurred_at, event.kind, event.resource_id, event.subject_id
                )
            )
            self._pending.add(
                PendingAnalysis(event.kind, event.resource_id, event.subject_id)
            )
        for row in reversed(self.decisions):
            self._trail.record(
                DecisionEntry(
                    row.id,
                    row.action,
                    row.field_path,
                    row.proposed_value,
                    row.chosen_value,
                    row.created_at,
                )
            )

    def as_json(self, *, exclude_plan_id: int | None = None) -> str:
        now = datetime.now(timezone.utc)
        upcoming = list(
            self._schedule.between(now - timedelta(days=30), now + timedelta(days=90))
        )
        pending: list[dict[str, Any]] = []
        while (item := self._pending.take()) is not None:
            pending.append({"kind": item.kind, "id": item.resource_id})
        data = {
            "evidence_catalog": self.evidence_catalog,
            "questionnaire_answers": self.questionnaire.answers
            if self.questionnaire
            else {},
            "subjects": [
                {
                    "id": row.id,
                    "name": row.name,
                    "difficulty": row.difficulty,
                    "status": row.status,
                }
                for row in self.subjects
            ],
            "activities": [
                {
                    "id": row.id,
                    "subject_id": row.subject_id,
                    "deadline": row.deadline.isoformat(),
                    "priority": row.priority,
                    "status": row.status,
                    "estimated_minutes": row.estimated_duration,
                    "title": row.title,
                    "deadline_revisions": row.deadline_revision,
                }
                for row in self.activities
            ],
            "sessions": [
                {
                    "id": row.id,
                    "subject_id": row.subject_id,
                    "activity_id": row.activity_id,
                    "planned_start_at": row.planned_start_at.isoformat(),
                    "planned_minutes": row.planned_duration,
                    "actual_minutes": float(row.actual_duration),
                    "lifecycle": row.execution_state,
                    "result": row.status,
                }
                for row in self.sessions
            ],
            "previous_plans": [
                {
                    "id": row.id,
                    "source": row.source,
                    "status": row.status,
                    "start_at": row.start_at.isoformat(),
                    "end_at": row.end_at.isoformat(),
                }
                for row in self.plans
                if row.id != exclude_plan_id
            ],
            "previous_challenges": [
                {
                    "id": row.id,
                    "plan_id": row.plan_id,
                    "status": row.status,
                    "target_type": row.target_type,
                    "subject_id": row.subject_id,
                    "activity_id": row.activity_id,
                    "session_id": row.study_session_id,
                }
                for row in self.challenges
            ],
            "user_decisions": [
                {"action": row.action, "field_path": row.field_path}
                for row in self._trail.backward()
            ],
            "finished_valid_sessions": self.finished_count,
            "chronological_events": [
                {"kind": row.kind, "id": row.resource_id} for row in self._journey
            ],
            "nearby_schedule": [
                {"kind": row.kind, "id": row.resource_id} for row in upcoming
            ],
            "analysis_candidates": pending,
        }
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
