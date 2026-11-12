from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.structures.study_range_insights import (
    StudyInterval,
    StudyRangeInsights,
)
from app.models.study_session import StudySession
from app.models.study_session_interval import StudySessionInterval
from app.models.subject import Subject
from app.schemas.analytics_study_time_bucket import AnalyticsStudyTimeBucket
from app.schemas.analytics_study_time_filters import AnalyticsStudyTimeFilters
from app.schemas.analytics_study_time_response import AnalyticsStudyTimeResponse
from app.schemas.analytics_study_time_subject import AnalyticsStudyTimeSubject


class AnalyticsStudyTimeService:
    """Aggregates exact closed interval time into timezone-aware buckets."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(
        self, user_id: int, filters: AnalyticsStudyTimeFilters
    ) -> AnalyticsStudyTimeResponse:
        start_utc = filters.from_at.astimezone(timezone.utc)
        end_utc = filters.to_at.astimezone(timezone.utc)
        rows = self._db.execute(
            select(
                StudySessionInterval.session_id,
                StudySession.subject_id,
                StudySessionInterval.started_at,
                StudySessionInterval.ended_at,
            )
            .join(StudySession, StudySession.id == StudySessionInterval.session_id)
            .where(
                StudySession.user_id == user_id,
                StudySessionInterval.ended_at.is_not(None),
                StudySessionInterval.started_at < end_utc,
                StudySessionInterval.ended_at > start_utc,
            )
        ).all()
        intervals = [
            StudyInterval(
                session_id=row.session_id,
                subject_id=row.subject_id,
                started_at=row.started_at,
                ended_at=row.ended_at,
            )
            for row in rows
            if row.ended_at is not None
        ]
        insights = StudyRangeInsights(intervals)
        totals = insights.between(start_utc, end_utc)
        subject_ids = [
            subject_id for subject_id, total in totals.items() if total.session_count
        ]
        names = (
            {
                subject.id: subject.name
                for subject in self._db.scalars(
                    select(Subject).where(
                        Subject.user_id == user_id, Subject.id.in_(subject_ids)
                    )
                ).all()
            }
            if subject_ids
            else {}
        )
        by_subject = [
            AnalyticsStudyTimeSubject(
                subject_id=subject_id,
                name=names[subject_id],
                seconds=self._seconds(total.duration_microseconds),
                minutes=self._minutes(total.duration_microseconds),
                sessions_count=total.session_count,
            )
            for subject_id, total in totals.items()
            if total.session_count and subject_id in names
        ]
        bucket_responses: list[AnalyticsStudyTimeBucket] = []
        bucket_ranges = self._buckets(
            filters.from_at, filters.to_at, filters.timezone, filters.granularity
        )
        for bucket_start, bucket_end in bucket_ranges:
            bucket_totals = insights.between(
                bucket_start.astimezone(timezone.utc),
                bucket_end.astimezone(timezone.utc),
            )
            duration = sum(
                item.duration_microseconds for item in bucket_totals.values()
            )
            bucket_responses.append(
                AnalyticsStudyTimeBucket(
                    from_at=bucket_start,
                    to_at=bucket_end,
                    seconds=self._seconds(duration),
                    minutes=self._minutes(duration),
                )
            )
        total_duration = sum(item.duration_microseconds for item in totals.values())
        return AnalyticsStudyTimeResponse(
            from_at=filters.from_at,
            to_at=filters.to_at,
            timezone=filters.timezone,
            granularity=filters.granularity,
            total_seconds=self._seconds(total_duration),
            total_minutes=self._minutes(total_duration),
            sessions_count=sum(item.session_count for item in totals.values()),
            by_subject=by_subject,
            buckets=bucket_responses,
        )

    @classmethod
    def _buckets(
        cls, start: datetime, end: datetime, zone_name: str, granularity: str
    ) -> list[tuple[datetime, datetime]]:
        zone = ZoneInfo(zone_name)
        start_local = start.astimezone(zone)
        end_utc = end.astimezone(timezone.utc)
        cursor = cls._floor(start_local, granularity)
        ranges: list[tuple[datetime, datetime]] = []
        while cursor.astimezone(timezone.utc) < end_utc:
            next_cursor = cls._next(cursor, granularity)
            clipped_start = max(
                start.astimezone(timezone.utc), cursor.astimezone(timezone.utc)
            )
            clipped_end = min(end_utc, next_cursor.astimezone(timezone.utc))
            if clipped_start < clipped_end:
                ranges.append(
                    (clipped_start.astimezone(zone), clipped_end.astimezone(zone))
                )
            cursor = next_cursor
        return ranges

    @staticmethod
    def _floor(value: datetime, granularity: str) -> datetime:
        midnight = datetime.combine(value.date(), time.min, tzinfo=value.tzinfo)
        if granularity == "day":
            return midnight
        if granularity == "week":
            return midnight - timedelta(days=midnight.weekday())
        return datetime(value.year, value.month, 1, tzinfo=value.tzinfo)

    @staticmethod
    def _next(value: datetime, granularity: str) -> datetime:
        if granularity == "day":
            return value + timedelta(days=1)
        if granularity == "week":
            return value + timedelta(days=7)
        if value.month == 12:
            return datetime(value.year + 1, 1, 1, tzinfo=value.tzinfo)
        return datetime(value.year, value.month + 1, 1, tzinfo=value.tzinfo)

    @staticmethod
    def _seconds(microseconds: int) -> str:
        return f"{Decimal(microseconds) / Decimal(1_000_000):.6f}"

    @classmethod
    def _minutes(cls, microseconds: int) -> str:
        return f"{Decimal(microseconds) / Decimal(60_000_000):.6f}"


__all__ = ["AnalyticsStudyTimeService"]
