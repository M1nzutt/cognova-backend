from decimal import Decimal
from typing import cast

from sqlalchemy import case, func, select, union
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.study_plans import StudyChallenge, StudyPlan
from app.models.study_session import StudySession
from app.schemas.analytics_overview import AnalyticsOverview


class AnalyticsOverviewService:
    """Builds descriptive all-time counters from the authenticated user's rows."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, user_id: int) -> AnalyticsOverview:
        total_duration = self._db.scalar(
            select(func.coalesce(func.sum(StudySession.actual_duration), 0)).where(
                StudySession.user_id == user_id
            )
        )
        session_counts = self._db.execute(
            select(
                func.sum(
                    case((StudySession.execution_state == "finished", 1), else_=0)
                ),
                func.sum(case((StudySession.status == "completed", 1), else_=0)),
                func.sum(case((StudySession.status == "partial", 1), else_=0)),
                func.sum(case((StudySession.status == "postponed", 1), else_=0)),
                func.sum(case((StudySession.status == "cancelled", 1), else_=0)),
            ).where(StudySession.user_id == user_id)
        ).one()
        activity_counts = self._db.execute(
            select(
                func.sum(case((Activity.status == "completed", 1), else_=0)),
                func.sum(case((Activity.status == "pending", 1), else_=0)),
                func.sum(case((Activity.status == "in_progress", 1), else_=0)),
            ).where(Activity.user_id == user_id)
        ).one()
        plan_counts = self._db.execute(
            select(
                func.sum(case((StudyPlan.status == "active", 1), else_=0)),
                func.sum(case((StudyPlan.status == "completed", 1), else_=0)),
            ).where(StudyPlan.user_id == user_id)
        ).one()
        challenge_counts = self._db.execute(
            select(
                func.sum(case((StudyChallenge.status == "completed", 1), else_=0)),
                func.sum(case((StudyChallenge.status == "failed", 1), else_=0)),
            ).where(StudyChallenge.user_id == user_id)
        ).one()
        activity_subjects = select(Activity.subject_id).where(
            Activity.user_id == user_id
        )
        session_subjects = select(StudySession.subject_id).where(
            StudySession.user_id == user_id
        )
        subjects = union(activity_subjects, session_subjects).subquery()
        subjects_with_activity = self._db.scalar(
            select(func.count()).select_from(subjects)
        )
        seconds = Decimal(str(total_duration or 0)).quantize(Decimal("0.000001"))
        return AnalyticsOverview(
            total_studied_seconds=f"{seconds:.6f}",
            total_studied_minutes=f"{seconds / Decimal(60):.6f}",
            finished_sessions=self._count(session_counts[0]),
            completed_sessions=self._count(session_counts[1]),
            partial_sessions=self._count(session_counts[2]),
            postponed_sessions=self._count(session_counts[3]),
            cancelled_sessions=self._count(session_counts[4]),
            subjects_with_activity=int(subjects_with_activity or 0),
            completed_activities=self._count(activity_counts[0]),
            pending_activities=self._count(activity_counts[1]),
            in_progress_activities=self._count(activity_counts[2]),
            active_plans=self._count(plan_counts[0]),
            completed_plans=self._count(plan_counts[1]),
            completed_challenges=self._count(challenge_counts[0]),
            failed_challenges=self._count(challenge_counts[1]),
        )

    @staticmethod
    def _count(value: object) -> int:
        count = cast(int | Decimal | None, value)
        return int(count) if count is not None else 0


__all__ = ["AnalyticsOverviewService"]
