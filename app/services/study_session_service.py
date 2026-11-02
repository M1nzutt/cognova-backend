import time
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import TypeVar

from sqlalchemy import and_, or_, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.domain_error import DomainError
from app.models.activity import Activity
from app.models.study_session import StudySession
from app.models.study_session_interval import StudySessionInterval
from app.models.subject import Subject
from app.models.user import User
from app.schemas.study_session_cursor import StudySessionCursor
from app.schemas.study_session_detail import StudySessionDetail
from app.schemas.study_session_filters import StudySessionFilters
from app.schemas.study_session_finish import StudySessionFinish
from app.schemas.study_session_interval_response import StudySessionIntervalResponse
from app.schemas.study_session_list_response import StudySessionListResponse
from app.schemas.study_session_summary import StudySessionSummary
from app.schemas.study_session_write import StudySessionWrite
from app.study_sessions.timer import elapsed_seconds, strictly_after, utc_now
from app.study_sessions.transitions import (
    require_finish,
    require_pause,
    require_planned,
    require_resume,
    require_start,
)

T = TypeVar("T")


class StudySessionService:
    """Own session reads and atomic planning/timer writes."""

    def __init__(
        self, db: Session, clock: Callable[[], datetime] | None = None
    ) -> None:
        self._db = db
        self._clock = clock or utc_now

    def list(
        self, user_id: int, filters: StudySessionFilters
    ) -> StudySessionListResponse:
        query = select(StudySession).where(StudySession.user_id == user_id)
        for name in ("subject_id", "activity_id", "execution_state", "status"):
            value = getattr(filters, name)
            if value is not None:
                query = query.where(getattr(StudySession, name) == value)
        if filters.planned_start_from is not None:
            query = query.where(
                StudySession.planned_start_at >= filters.planned_start_from
            )
        if filters.planned_start_to is not None:
            query = query.where(
                StudySession.planned_start_at < filters.planned_start_to
            )
        if filters.after_planned_start_at is not None and filters.after_id is not None:
            query = query.where(
                or_(
                    StudySession.planned_start_at > filters.after_planned_start_at,
                    and_(
                        StudySession.planned_start_at == filters.after_planned_start_at,
                        StudySession.id > filters.after_id,
                    ),
                )
            )
        rows = self._db.scalars(
            query.order_by(StudySession.planned_start_at, StudySession.id).limit(
                filters.limit + 1
            )
        ).all()
        page = rows[: filters.limit]
        items = [StudySessionSummary.model_validate(row) for row in page]
        cursor = None
        if len(rows) > filters.limit and page:
            last = page[-1]
            cursor = StudySessionCursor(
                after_planned_start_at=last.planned_start_at, after_id=last.id
            )
        return StudySessionListResponse(items=items, next_cursor=cursor)

    def detail(self, user_id: int, session_id: int) -> StudySessionDetail:
        return self._detail(self._owned(user_id, session_id))

    def create(self, user_id: int, data: StudySessionWrite) -> StudySessionDetail:
        def insert() -> StudySessionDetail:
            self._validate_assignment(user_id, data.subject_id, data.activity_id)
            record = StudySession(
                user_id=user_id,
                subject_id=data.subject_id,
                activity_id=data.activity_id,
                planned_start_at=data.planned_start_at,
                planned_duration=data.planned_duration,
                execution_state="planned",
                actual_duration=Decimal(0),
            )
            self._db.add(record)
            self._db.flush()
            return self._detail(record)

        return self._write(user_id, insert)

    def update(
        self, user_id: int, session_id: int, data: StudySessionWrite
    ) -> StudySessionDetail:
        def replace_plan() -> StudySessionDetail:
            record = self._owned(user_id, session_id, lock=True)
            require_planned(record.execution_state)
            if self._has_intervals(session_id):
                raise DomainError("STUDY_SESSION_TRANSITION_CONFLICT")
            self._validate_assignment(user_id, data.subject_id, data.activity_id)
            record.subject_id = data.subject_id
            record.activity_id = data.activity_id
            record.planned_start_at = data.planned_start_at
            record.planned_duration = data.planned_duration
            self._db.flush()
            return self._detail(record)

        return self._write(user_id, replace_plan)

    def delete(self, user_id: int, session_id: int) -> None:
        def remove() -> None:
            record = self._owned(user_id, session_id, lock=True)
            if record.execution_state != "planned" or self._has_intervals(session_id):
                raise DomainError("STUDY_SESSION_HISTORY_CONFLICT")
            self._db.delete(record)
            self._db.flush()

        self._write(user_id, remove)

    def start(self, user_id: int, session_id: int) -> StudySessionDetail:
        def begin() -> StudySessionDetail:
            record = self._owned(user_id, session_id, lock=True)
            require_start(record.execution_state)
            self._require_no_other_active(user_id, session_id)
            started_at = self._clock()
            if started_at.tzinfo is None:
                raise ValueError("Timer clock must be timezone-aware")
            record.execution_state = "running"
            record.start_at = started_at
            self._db.add(
                StudySessionInterval(session_id=session_id, started_at=started_at)
            )
            self._db.flush()
            return self._detail(record)

        return self._write(user_id, begin)

    def pause(self, user_id: int, session_id: int) -> StudySessionDetail:
        def stop_interval() -> StudySessionDetail:
            record = self._owned(user_id, session_id, lock=True)
            require_pause(record.execution_state)
            interval = self._open_interval(session_id)
            interval.ended_at = strictly_after(self._clock(), interval.started_at)
            self._db.flush()
            record.actual_duration = self._closed_duration(session_id)
            record.execution_state = "paused"
            self._db.flush()
            return self._detail(record)

        return self._write(user_id, stop_interval)

    def resume(self, user_id: int, session_id: int) -> StudySessionDetail:
        def continue_timer() -> StudySessionDetail:
            record = self._owned(user_id, session_id, lock=True)
            require_resume(record.execution_state)
            self._require_no_other_active(user_id, session_id)
            last = self._db.scalar(
                select(StudySessionInterval)
                .where(StudySessionInterval.session_id == session_id)
                .order_by(
                    StudySessionInterval.started_at.desc(),
                    StudySessionInterval.id.desc(),
                )
                .limit(1)
                .with_for_update()
            )
            if last is None or last.ended_at is None:
                raise DomainError("STUDY_SESSION_TRANSITION_CONFLICT")
            started_at = strictly_after(self._clock(), last.ended_at)
            record.execution_state = "running"
            self._db.add(
                StudySessionInterval(session_id=session_id, started_at=started_at)
            )
            self._db.flush()
            return self._detail(record)

        return self._write(user_id, continue_timer)

    def finish(
        self, user_id: int, session_id: int, data: StudySessionFinish
    ) -> StudySessionDetail:
        def complete() -> StudySessionDetail:
            record = self._owned(user_id, session_id, lock=True)
            require_finish(record.execution_state, data.status)
            if record.execution_state == "planned":
                if data.context is not None or data.other_text is not None:
                    raise DomainError("STUDY_SESSION_TRANSITION_CONFLICT")
                record.execution_state = "finished"
                record.status = data.status
                self._db.flush()
                return self._detail(record)

            if record.execution_state == "running":
                interval = self._open_interval(session_id)
                ended_at = strictly_after(self._clock(), interval.started_at)
                interval.ended_at = ended_at
                self._db.flush()
            else:
                last = self._db.scalar(
                    select(StudySessionInterval)
                    .where(StudySessionInterval.session_id == session_id)
                    .order_by(
                        StudySessionInterval.started_at.desc(),
                        StudySessionInterval.id.desc(),
                    )
                    .limit(1)
                    .with_for_update()
                )
                if last is None or last.ended_at is None or record.start_at is None:
                    raise DomainError("STUDY_SESSION_TRANSITION_CONFLICT")
                ended_at = strictly_after(
                    self._clock(), max(last.ended_at, record.start_at)
                )

            record.execution_state = "finished"
            record.status = data.status
            record.context = data.context
            record.other_text = data.other_text
            record.end_at = ended_at
            record.actual_duration = self._closed_duration(session_id)
            self._db.flush()
            return self._detail(record)

        return self._write(user_id, complete)

    def _validate_assignment(
        self, user_id: int, subject_id: int, activity_id: int | None
    ) -> None:
        if (
            self._db.scalar(
                select(Subject.id).where(
                    Subject.user_id == user_id, Subject.id == subject_id
                )
            )
            is None
        ):
            raise DomainError("SUBJECT_NOT_FOUND")
        if activity_id is not None and (
            self._db.scalar(
                select(Activity.id).where(
                    Activity.user_id == user_id,
                    Activity.subject_id == subject_id,
                    Activity.id == activity_id,
                )
            )
            is None
        ):
            raise DomainError("ACTIVITY_NOT_FOUND")

    def _require_no_other_active(self, user_id: int, session_id: int) -> None:
        active = self._db.scalar(
            select(StudySession.id)
            .where(
                StudySession.user_id == user_id,
                StudySession.id != session_id,
                StudySession.execution_state.in_(("running", "paused")),
            )
            .limit(1)
        )
        if active is not None:
            raise DomainError("STUDY_SESSION_ACTIVE_CONFLICT")

    def _owned(
        self, user_id: int, session_id: int, *, lock: bool = False
    ) -> StudySession:
        query = select(StudySession).where(
            StudySession.id == session_id, StudySession.user_id == user_id
        )
        if lock:
            query = query.with_for_update()
        record = self._db.scalar(query.execution_options(populate_existing=True))
        if record is None:
            raise DomainError("STUDY_SESSION_NOT_FOUND")
        return record

    def _has_intervals(self, session_id: int) -> bool:
        return (
            self._db.scalar(
                select(StudySessionInterval.id)
                .where(StudySessionInterval.session_id == session_id)
                .limit(1)
            )
            is not None
        )

    def _open_interval(self, session_id: int) -> StudySessionInterval:
        interval = self._db.scalar(
            select(StudySessionInterval)
            .where(
                StudySessionInterval.session_id == session_id,
                StudySessionInterval.ended_at.is_(None),
            )
            .with_for_update()
        )
        if interval is None:
            raise DomainError("STUDY_SESSION_TRANSITION_CONFLICT")
        return interval

    def _closed_duration(self, session_id: int) -> Decimal:
        rows = self._db.scalars(
            select(StudySessionInterval).where(
                StudySessionInterval.session_id == session_id,
                StudySessionInterval.ended_at.is_not(None),
            )
        ).all()
        return elapsed_seconds((row.started_at, row.ended_at) for row in rows)

    def _detail(self, record: StudySession) -> StudySessionDetail:
        self._db.flush()
        self._db.refresh(record)
        intervals = self._db.scalars(
            select(StudySessionInterval)
            .where(StudySessionInterval.session_id == record.id)
            .order_by(StudySessionInterval.started_at, StudySessionInterval.id)
        ).all()
        summary = StudySessionSummary.model_validate(record)
        return StudySessionDetail(
            **summary.model_dump(),
            other_text=record.other_text,
            intervals=[
                StudySessionIntervalResponse.model_validate(interval)
                for interval in intervals
            ],
        )

    def _write(self, user_id: int, operation: Callable[[], T]) -> T:
        self._db.rollback()
        for attempt in range(3):
            try:
                self._db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                owner = self._db.scalar(
                    select(User.id).where(User.id == user_id).with_for_update()
                )
                if owner is None:
                    raise DomainError("STUDY_SESSION_NOT_FOUND")
                result = operation()
                self._db.commit()
                return result
            except DomainError:
                self._db.rollback()
                raise
            except DBAPIError as exc:
                self._db.rollback()
                state = getattr(exc.orig, "sqlstate", None)
                constraint = getattr(
                    getattr(exc.orig, "diag", None), "constraint_name", None
                )
                if state in {"40001", "40P01"}:
                    if attempt < 2:
                        time.sleep(0.01 * (attempt + 1))
                        continue
                    raise DomainError("STUDY_SESSION_WRITE_CONFLICT") from None
                if constraint == "uq_study_sessions_user_executing":
                    raise DomainError("STUDY_SESSION_ACTIVE_CONFLICT") from None
                if constraint in {
                    "uq_study_intervals_open",
                    "ex_study_intervals_overlap",
                }:
                    raise DomainError("STUDY_SESSION_TRANSITION_CONFLICT") from None
                if constraint == "fk_study_sessions_owner_subject":
                    raise DomainError("SUBJECT_NOT_FOUND") from None
                if constraint == "fk_study_sessions_owner_subject_activity":
                    raise DomainError("ACTIVITY_NOT_FOUND") from None
                if constraint == "fk_study_intervals_session":
                    raise DomainError("STUDY_SESSION_HISTORY_CONFLICT") from None
                if state == "23P01" or state == "23514":
                    raise DomainError("STUDY_SESSION_TRANSITION_CONFLICT") from None
                raise
            except Exception:
                self._db.rollback()
                raise
        raise AssertionError("unreachable")


__all__ = ["StudySessionService"]
