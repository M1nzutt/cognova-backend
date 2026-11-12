from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.analytics.structures.analytics_resource import AnalyticsResource
from app.analytics.structures.balanced_timeline import BalancedTimeline
from app.analytics.structures.entries import TimelineEvent
from app.analytics.structures.resource_directory import ResourceDirectory
from app.models.activity import Activity
from app.models.study_plans import StudyChallenge, StudyPlan
from app.models.study_session import StudySession
from app.models.subject import Subject


class TimelineCurrentEvents:
    """Indexes current resource facts that belong in an analytics timeline."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def activities(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        directory: ResourceDirectory,
        index: BalancedTimeline,
    ) -> None:
        rows = self._db.execute(
            select(Activity, Subject.name)
            .join(
                Subject,
                and_(Subject.id == Activity.subject_id, Subject.user_id == user_id),
            )
            .where(
                Activity.user_id == user_id,
                or_(
                    and_(Activity.created_at >= start, Activity.created_at < end),
                    and_(Activity.deadline >= start, Activity.deadline < end),
                ),
            )
        ).all()
        for activity, subject_name in rows:
            self._add_subject(directory, activity.subject_id, subject_name)
            directory.put(
                AnalyticsResource(
                    "activity",
                    activity.id,
                    activity.title,
                    subject_id=activity.subject_id,
                    status=activity.status,
                )
            )
            if start <= activity.created_at < end:
                index.add(
                    TimelineEvent(
                        activity.created_at,
                        "activity",
                        "activity",
                        activity.id,
                        activity.id,
                        "created",
                    )
                )
            if start <= activity.deadline < end:
                index.add(
                    TimelineEvent(
                        activity.deadline,
                        "activity",
                        "activity",
                        activity.id,
                        0,
                        "deadline",
                        {"deadline": activity.deadline},
                    )
                )

    def planned_sessions(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        directory: ResourceDirectory,
        index: BalancedTimeline,
    ) -> None:
        rows = self._db.execute(
            select(StudySession, Subject.name)
            .join(
                Subject,
                and_(Subject.id == StudySession.subject_id, Subject.user_id == user_id),
            )
            .where(
                StudySession.user_id == user_id,
                StudySession.planned_start_at >= start,
                StudySession.planned_start_at < end,
            )
        ).all()
        for session, subject_name in rows:
            self._add_subject(directory, session.subject_id, subject_name)
            directory.put(
                AnalyticsResource(
                    "study_session",
                    session.id,
                    subject_name,
                    subject_id=session.subject_id,
                )
            )
            index.add(
                TimelineEvent(
                    session.planned_start_at,
                    "study_session",
                    "study_session",
                    session.id,
                    0,
                    "planned",
                    {"planned_duration": session.planned_duration},
                )
            )

    def plans(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        directory: ResourceDirectory,
        index: BalancedTimeline,
    ) -> None:
        plans = self._db.scalars(
            select(StudyPlan).where(
                StudyPlan.user_id == user_id,
                StudyPlan.created_at >= start,
                StudyPlan.created_at < end,
            )
        ).all()
        for plan in plans:
            directory.put(AnalyticsResource("study_plan", plan.id, plan.name))
            index.add(
                TimelineEvent(
                    plan.created_at,
                    "plan",
                    "study_plan",
                    plan.id,
                    0,
                    "created",
                    {"source": plan.source},
                )
            )

    def challenges(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        directory: ResourceDirectory,
        index: BalancedTimeline,
    ) -> None:
        rows = self._db.execute(
            select(StudyChallenge, Subject.name)
            .outerjoin(
                Subject,
                and_(
                    Subject.id == StudyChallenge.subject_id,
                    Subject.user_id == user_id,
                ),
            )
            .where(
                StudyChallenge.user_id == user_id,
                StudyChallenge.created_at >= start,
                StudyChallenge.created_at < end,
            )
        ).all()
        for challenge, subject_name in rows:
            if challenge.subject_id is not None and subject_name is not None:
                self._add_subject(directory, challenge.subject_id, subject_name)
            directory.put(
                AnalyticsResource(
                    "study_challenge",
                    challenge.id,
                    challenge.title,
                    subject_id=challenge.subject_id,
                    plan_id=challenge.plan_id,
                    status=challenge.status,
                )
            )
            index.add(
                TimelineEvent(
                    challenge.created_at,
                    "challenge",
                    "study_challenge",
                    challenge.id,
                    0,
                    "created",
                    {"plan_id": challenge.plan_id},
                )
            )

    @staticmethod
    def _add_subject(directory: ResourceDirectory, subject_id: int, name: str) -> None:
        directory.put(AnalyticsResource("subject", subject_id, name))


__all__ = ["TimelineCurrentEvents"]
