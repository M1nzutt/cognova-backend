from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.domain_error import DomainError
from app.models.activity import Activity
from app.models.study_plans import (
    StudyPlan,
    StudyPlanActivity,
    StudyPlanSession,
    StudyPlanSubject,
)
from app.models.study_session import StudySession
from app.models.subject import Subject
from app.schemas.study_plan_write import StudyPlanWrite


class StudyPlanResources:
    """Validates and maintains Plan links to existing academic resources."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def validate(
        self, user_id: int, data: StudyPlanWrite
    ) -> tuple[list[Activity], list[StudySession]]:
        subjects = self._db.scalars(
            select(Subject.id).where(
                Subject.user_id == user_id, Subject.id.in_(data.subject_ids)
            )
        ).all()
        if set(subjects) != set(data.subject_ids):
            raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT")
        activities = list(
            self._db.scalars(
                select(Activity).where(
                    Activity.user_id == user_id,
                    Activity.id.in_(data.activity_ids),
                )
            ).all()
        )
        if {row.id for row in activities} != set(data.activity_ids):
            raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT")
        sessions = list(
            self._db.scalars(
                select(StudySession).where(
                    StudySession.user_id == user_id,
                    StudySession.id.in_(data.study_session_ids),
                )
            ).all()
        )
        if {row.id for row in sessions} != set(data.study_session_ids):
            raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT")
        subject_ids = set(data.subject_ids)
        activity_ids = set(data.activity_ids)
        if any(activity.subject_id not in subject_ids for activity in activities):
            raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT")
        if any(
            session.subject_id not in subject_ids
            or (
                session.activity_id is not None
                and session.activity_id not in activity_ids
            )
            for session in sessions
        ):
            raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT")
        return activities, sessions

    @staticmethod
    def validate_schedule(
        start_at: datetime, end_at: datetime, sessions: list[StudySession]
    ) -> None:
        for session in sessions:
            session_end = session.planned_start_at + timedelta(
                minutes=session.planned_duration
            )
            if session.planned_start_at < start_at or session_end > end_at:
                raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT")

    def replace(
        self,
        user_id: int,
        plan_id: int,
        data: StudyPlanWrite,
        activities: list[Activity],
        sessions: list[StudySession],
    ) -> None:
        selected_subjects = set(data.subject_ids)
        selected_activities = {row.id for row in activities}
        selected_sessions = {row.id for row in sessions}
        current_subjects = self._current_ids(
            StudyPlanSubject, StudyPlanSubject.subject_id, user_id, plan_id
        )
        current_activities = self._current_ids(
            StudyPlanActivity, StudyPlanActivity.activity_id, user_id, plan_id
        )
        current_sessions = self._current_ids(
            StudyPlanSession, StudyPlanSession.study_session_id, user_id, plan_id
        )

        # Remove child links before their Plan→Subject parent links.
        self._remove_missing(
            StudyPlanActivity,
            StudyPlanActivity.activity_id,
            user_id,
            plan_id,
            current_activities - selected_activities,
        )
        self._remove_missing(
            StudyPlanSession,
            StudyPlanSession.study_session_id,
            user_id,
            plan_id,
            current_sessions - selected_sessions,
        )
        self._remove_missing(
            StudyPlanSubject,
            StudyPlanSubject.subject_id,
            user_id,
            plan_id,
            current_subjects - selected_subjects,
        )

        for subject_id in sorted(selected_subjects - current_subjects):
            self._db.add(
                StudyPlanSubject(
                    user_id=user_id, plan_id=plan_id, subject_id=subject_id
                )
            )
        self._db.flush()

        activity_subjects = {row.id: row.subject_id for row in activities}
        for activity_id in sorted(selected_activities - current_activities):
            self._db.add(
                StudyPlanActivity(
                    user_id=user_id,
                    plan_id=plan_id,
                    subject_id=activity_subjects[activity_id],
                    activity_id=activity_id,
                )
            )
        session_subjects = {row.id: row.subject_id for row in sessions}
        for session_id in sorted(selected_sessions - current_sessions):
            self._db.add(
                StudyPlanSession(
                    user_id=user_id,
                    plan_id=plan_id,
                    subject_id=session_subjects[session_id],
                    study_session_id=session_id,
                )
            )
        self._db.flush()

    def snapshot(self, plan: StudyPlan) -> dict[str, object]:
        return {
            "name": plan.name,
            "objective": plan.objective,
            "start_at": plan.start_at.isoformat(),
            "end_at": plan.end_at.isoformat(),
            "subject_ids": list(
                self._db.scalars(
                    select(StudyPlanSubject.subject_id)
                    .where(
                        StudyPlanSubject.user_id == plan.user_id,
                        StudyPlanSubject.plan_id == plan.id,
                    )
                    .order_by(StudyPlanSubject.subject_id)
                ).all()
            ),
            "activity_ids": list(
                self._db.scalars(
                    select(StudyPlanActivity.activity_id)
                    .where(
                        StudyPlanActivity.user_id == plan.user_id,
                        StudyPlanActivity.plan_id == plan.id,
                    )
                    .order_by(StudyPlanActivity.activity_id)
                ).all()
            ),
            "study_session_ids": list(
                self._db.scalars(
                    select(StudyPlanSession.study_session_id)
                    .where(
                        StudyPlanSession.user_id == plan.user_id,
                        StudyPlanSession.plan_id == plan.id,
                    )
                    .order_by(StudyPlanSession.study_session_id)
                ).all()
            ),
        }

    def validate_current(self, plan: StudyPlan) -> None:
        data = StudyPlanWrite.model_validate(self.snapshot(plan))
        _, sessions = self.validate(plan.user_id, data)
        self.validate_schedule(data.start_at, data.end_at, sessions)

    def restore_field(self, plan: StudyPlan, field_path: str, value: object) -> None:
        if field_path not in {"subject_ids", "activity_ids", "study_session_ids"}:
            raise DomainError("STUDY_PLAN_HISTORY_CONFLICT")
        if not isinstance(value, list) or any(type(item) is not int for item in value):
            raise DomainError("STUDY_PLAN_HISTORY_CONFLICT")
        snapshot = self.snapshot(plan)
        snapshot[field_path] = value
        data = StudyPlanWrite.model_validate(snapshot)
        activities, sessions = self.validate(plan.user_id, data)
        self.validate_schedule(data.start_at, data.end_at, sessions)
        self.replace(plan.user_id, plan.id, data, activities, sessions)

    def _current_ids(
        self,
        model: Any,
        id_column: Any,
        user_id: int,
        plan_id: int,
    ) -> set[int]:
        return set(
            self._db.scalars(
                select(id_column).where(
                    model.user_id == user_id, model.plan_id == plan_id
                )
            ).all()
        )

    def _remove_missing(
        self,
        model: Any,
        id_column: Any,
        user_id: int,
        plan_id: int,
        removed: set[int],
    ) -> None:
        if removed:
            self._db.execute(
                delete(model).where(
                    model.user_id == user_id,
                    model.plan_id == plan_id,
                    id_column.in_(removed),
                )
            )


__all__ = ["StudyPlanResources"]
