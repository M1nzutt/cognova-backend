from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.analytics.structures.academic_archive import AcademicArchive
from app.analytics.structures.analytics_resource import AnalyticsResource
from app.analytics.structures.entries import TimelineEvent
from app.analytics.structures.resource_directory import ResourceDirectory
from app.models.activity import Activity
from app.models.activity_deadline_event import ActivityDeadlineEvent
from app.models.study_plans import StudyPlan, StudyPlanDecision
from app.models.study_session import StudySession
from app.models.study_session_interval import StudySessionInterval
from app.models.subject import Subject


class TimelineHistoricalEvents:
    """Indexes persisted event records without inferring missing history."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def deadline_history(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        directory: ResourceDirectory,
        index: AcademicArchive,
    ) -> None:
        rows = self._db.execute(
            select(
                ActivityDeadlineEvent,
                Activity.id,
                Activity.title,
                Activity.subject_id,
                Subject.name,
            )
            .join(
                Activity,
                and_(
                    Activity.id == ActivityDeadlineEvent.activity_id,
                    Activity.user_id == user_id,
                ),
            )
            .join(
                Subject,
                and_(Subject.id == Activity.subject_id, Subject.user_id == user_id),
            )
            .where(
                ActivityDeadlineEvent.occurred_at >= start,
                ActivityDeadlineEvent.occurred_at < end,
            )
        ).all()
        for event, activity_id, title, subject_id, subject_name in rows:
            self._add_subject(directory, subject_id, subject_name)
            directory.put(
                AnalyticsResource("activity", activity_id, title, subject_id=subject_id)
            )
            index.add(
                TimelineEvent(
                    event.occurred_at,
                    "activity",
                    "activity",
                    activity_id,
                    event.revision,
                    "deadline_changed",
                    {
                        "event_type": event.event_type,
                        "previous_deadline": event.previous_deadline,
                        "new_deadline": event.new_deadline,
                    },
                )
            )

    def session_intervals(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        directory: ResourceDirectory,
        index: AcademicArchive,
    ) -> None:
        rows = self._db.execute(
            select(
                StudySessionInterval,
                StudySession.id,
                StudySession.subject_id,
                Subject.name,
            )
            .join(StudySession, StudySession.id == StudySessionInterval.session_id)
            .join(
                Subject,
                and_(Subject.id == StudySession.subject_id, Subject.user_id == user_id),
            )
            .where(
                StudySession.user_id == user_id,
                or_(
                    and_(
                        StudySessionInterval.started_at >= start,
                        StudySessionInterval.started_at < end,
                    ),
                    and_(
                        StudySessionInterval.ended_at >= start,
                        StudySessionInterval.ended_at < end,
                    ),
                ),
            )
        ).all()
        for interval, session_id, subject_id, subject_name in rows:
            self._add_subject(directory, subject_id, subject_name)
            directory.put(
                AnalyticsResource(
                    "study_session",
                    session_id,
                    subject_name,
                    subject_id=subject_id,
                )
            )
            if start <= interval.started_at < end:
                index.add(
                    TimelineEvent(
                        interval.started_at,
                        "study_session",
                        "study_session",
                        session_id,
                        interval.id,
                        "started",
                    )
                )
            if interval.ended_at is not None and start <= interval.ended_at < end:
                index.add(
                    TimelineEvent(
                        interval.ended_at,
                        "study_session",
                        "study_session",
                        session_id,
                        interval.id,
                        "ended",
                    )
                )

    def decisions(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        directory: ResourceDirectory,
        index: AcademicArchive,
    ) -> None:
        rows = self._db.execute(
            select(StudyPlanDecision, StudyPlan.name)
            .join(
                StudyPlan,
                and_(
                    StudyPlan.id == StudyPlanDecision.plan_id,
                    StudyPlan.user_id == StudyPlanDecision.user_id,
                ),
            )
            .where(
                StudyPlanDecision.user_id == user_id,
                StudyPlan.user_id == user_id,
                StudyPlanDecision.created_at >= start,
                StudyPlanDecision.created_at < end,
            )
        ).all()
        for decision, plan_name in rows:
            directory.put(AnalyticsResource("study_plan", decision.plan_id, plan_name))
            index.add(
                TimelineEvent(
                    decision.created_at,
                    "decision",
                    "study_plan",
                    decision.plan_id,
                    decision.id,
                    "decision",
                    {"action": decision.action, "field_path": decision.field_path},
                )
            )

    @staticmethod
    def _add_subject(directory: ResourceDirectory, subject_id: int, name: str) -> None:
        directory.put(AnalyticsResource("subject", subject_id, name))


__all__ = ["TimelineHistoricalEvents"]
