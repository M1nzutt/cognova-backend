from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.search_cursors import decode_search_cursor, encode_search_cursor
from app.analytics.structures.academic_finder import AcademicFinder
from app.analytics.structures.analytics_resource import AnalyticsResource
from app.analytics.structures.resource_directory import ResourceDirectory
from app.models.activity import Activity
from app.models.study_plans import StudyChallenge, StudyPlan
from app.models.subject import Subject
from app.schemas.analytics_search_filters import AnalyticsSearchFilters
from app.schemas.analytics_search_item import AnalyticsSearchItem
from app.schemas.analytics_search_response import AnalyticsSearchResponse


class AnalyticsSearchService:
    """Builds an owned-resource prefix index for one request."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def search(
        self, user_id: int, filters: AnalyticsSearchFilters
    ) -> AnalyticsSearchResponse:
        directory = ResourceDirectory()
        finder = AcademicFinder()
        resource_type = filters.type
        if resource_type in (None, "subject"):
            for subject in self._db.scalars(
                select(Subject).where(Subject.user_id == user_id)
            ).all():
                directory.put(
                    AnalyticsResource(
                        "subject", subject.id, subject.name, status=subject.status
                    )
                )
        if resource_type in (None, "activity"):
            rows = (
                self._db.execute(
                    select(Activity)
                    .join(Subject, Subject.id == Activity.subject_id)
                    .where(Activity.user_id == user_id, Subject.user_id == user_id)
                )
                .scalars()
                .all()
            )
            for activity in rows:
                directory.put(
                    AnalyticsResource(
                        "activity",
                        activity.id,
                        activity.title,
                        subject_id=activity.subject_id,
                        status=activity.status,
                    )
                )
        if resource_type in (None, "study_plan"):
            for plan in self._db.scalars(
                select(StudyPlan).where(StudyPlan.user_id == user_id)
            ).all():
                directory.put(
                    AnalyticsResource(
                        "study_plan", plan.id, plan.name, status=plan.status
                    )
                )
        if resource_type in (None, "study_challenge"):
            for challenge in self._db.scalars(
                select(StudyChallenge).where(StudyChallenge.user_id == user_id)
            ).all():
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
        for resource in directory.values():
            finder.add(resource)
        after_key = (
            decode_search_cursor(filters.cursor, filters.prefix, filters.type)
            if filters.cursor
            else None
        )
        resources = finder.search(
            filters.prefix,
            after_key=after_key,
            limit=filters.limit + 1,
        )
        has_more = len(resources) > filters.limit
        page = resources[: filters.limit]
        next_cursor = (
            encode_search_cursor(
                finder.sort_key(page[-1]), filters.prefix, filters.type
            )
            if has_more and page
            else None
        )
        return AnalyticsSearchResponse(
            items=[
                AnalyticsSearchItem(
                    type=resource.resource_type,
                    id=resource.resource_id,
                    title=resource.title,
                    subject_id=resource.subject_id,
                    plan_id=resource.plan_id,
                    status=resource.status,
                )
                for resource in page
            ],
            next_cursor=next_cursor,
        )


__all__ = ["AnalyticsSearchService"]
