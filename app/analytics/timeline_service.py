from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.analytics.cursors import decode_timeline_cursor, encode_timeline_cursor
from app.analytics.structures.academic_archive import AcademicArchive
from app.analytics.structures.analytics_resource import AnalyticsResource
from app.analytics.structures.balanced_timeline import BalancedTimeline
from app.analytics.structures.entries import TimelineEvent
from app.analytics.structures.resource_directory import ResourceDirectory
from app.models.activity import Activity
from app.models.activity_deadline_event import ActivityDeadlineEvent
from app.models.study_plans import StudyChallenge, StudyPlan, StudyPlanDecision
from app.models.study_session import StudySession
from app.models.study_session_interval import StudySessionInterval
from app.models.subject import Subject
from app.schemas.analytics_timeline_filters import AnalyticsTimelineFilters
from app.schemas.analytics_timeline_item import AnalyticsTimelineItem
from app.schemas.analytics_timeline_response import AnalyticsTimelineResponse


class AnalyticsTimelineService:
    """Builds mixed historical/planned timeline pages from owned source rows."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_page(
        self, user_id: int, filters: AnalyticsTimelineFilters
    ) -> AnalyticsTimelineResponse:
        start = filters.from_at.astimezone(timezone.utc)
        end = filters.to_at.astimezone(timezone.utc)
        after_key = (
            decode_timeline_cursor(filters.cursor, start, end, filters.category)
            if filters.cursor
            else None
        )
        history = AcademicArchive()
        current = BalancedTimeline()
        directory = ResourceDirectory()
        category = filters.category

        if category in (None, "activity"):
            self._add_activities(user_id, start, end, directory, current)
            self._add_deadline_history(user_id, start, end, directory, history)
        if category in (None, "study_session"):
            self._add_planned_sessions(user_id, start, end, directory, current)
            self._add_session_intervals(user_id, start, end, directory, history)
        if category in (None, "plan"):
            self._add_plans(user_id, start, end, directory, current)
        if category in (None, "decision"):
            self._add_decisions(user_id, start, end, directory, history)
        if category in (None, "challenge"):
            self._add_challenges(user_id, start, end, directory, current)

        candidates = self._merge(
            list(history.iter_range(start, end, after_key, filters.limit + 1)),
            list(current.iter_range(start, end, after_key, filters.limit + 1)),
            filters.limit + 1,
        )
        has_more = len(candidates) > filters.limit
        page_events = candidates[: filters.limit]
        items = [self._to_item(event, directory) for event in page_events]
        next_cursor = (
            encode_timeline_cursor(page_events[-1], start, end, filters.category)
            if has_more and page_events
            else None
        )
        return AnalyticsTimelineResponse(items=items, next_cursor=next_cursor)

    def _add_activities(
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

    def _add_deadline_history(
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

    def _add_planned_sessions(
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
                    {
                        "planned_duration": session.planned_duration,
                    },
                )
            )

    def _add_session_intervals(
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

    def _add_plans(
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

    def _add_decisions(
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

    def _add_challenges(
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

    @staticmethod
    def _merge(
        history: list[TimelineEvent],
        current: list[TimelineEvent],
        limit: int,
    ) -> list[TimelineEvent]:
        merged: list[TimelineEvent] = []
        left = right = 0
        while len(merged) < limit and (left < len(history) or right < len(current)):
            if right >= len(current) or (
                left < len(history) and history[left].key <= current[right].key
            ):
                merged.append(history[left])
                left += 1
            else:
                merged.append(current[right])
                right += 1
        return merged

    @staticmethod
    def _to_item(
        event: TimelineEvent, directory: ResourceDirectory
    ) -> AnalyticsTimelineItem:
        resource = directory.get((event.resource_type, event.resource_id))
        title = resource.title if resource is not None else "Recurso académico"
        subject_id = resource.subject_id if resource is not None else None
        subject = (
            directory.get(("subject", subject_id)) if subject_id is not None else None
        )
        if event.resource_type == "study_session":
            title = "Sesión de estudio"
        return AnalyticsTimelineItem(
            event_id=(
                f"{event.category}:{event.resource_id}:"
                f"{event.occurrence_id}:{event.event_type}"
            ),
            occurred_at=event.occurred_at.astimezone(timezone.utc),
            category=event.category,
            event_type=event.event_type,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            title=title,
            subject_id=subject_id,
            subject_name=subject.title if subject is not None else None,
            details=event.details,
        )


__all__ = ["AnalyticsTimelineService"]
