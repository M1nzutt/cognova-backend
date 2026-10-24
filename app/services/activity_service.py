import time
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.activities.transitions import validate_transition
from app.core.domain_error import DomainError
from app.models.activity import Activity
from app.models.activity_deadline_event import ActivityDeadlineEvent
from app.models.subject import Subject
from app.models.user import User
from app.schemas.activity_deadline_event_response import ActivityDeadlineEventResponse
from app.schemas.activity_deadline_request import ActivityDeadlineRequest
from app.schemas.activity_filters import ActivityFilters
from app.schemas.activity_history_response import ActivityHistoryResponse
from app.schemas.activity_list_response import ActivityListResponse
from app.schemas.activity_response import ActivityResponse
from app.schemas.activity_status_request import ActivityStatusRequest
from app.schemas.activity_write import ActivityWrite

T = TypeVar("T")


class ActivityService:
    """Own mutation transactions; never receive pending writes from callers."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def _owned(self, user_id: int, activity_id: int, *, lock: bool = False) -> Activity:
        query = select(Activity).where(
            Activity.id == activity_id, Activity.user_id == user_id
        )
        if lock:
            query = query.with_for_update()
        record = self._db.scalar(query.execution_options(populate_existing=True))
        if record is None:
            raise DomainError("ACTIVITY_NOT_FOUND")
        return record

    def _subject(self, user_id: int, subject_id: int) -> None:
        if (
            self._db.scalar(
                select(Subject.id).where(
                    Subject.id == subject_id, Subject.user_id == user_id
                )
            )
            is None
        ):
            raise DomainError("SUBJECT_NOT_FOUND")

    def detail(self, user_id: int, activity_id: int) -> ActivityResponse:
        return ActivityResponse.model_validate(self._owned(user_id, activity_id))

    def list(self, user_id: int, filters: ActivityFilters) -> ActivityListResponse:
        query = select(Activity).where(Activity.user_id == user_id)
        for field in ("subject_id", "status", "priority", "deadline"):
            value = getattr(filters, field)
            if value is not None:
                query = query.where(getattr(Activity, field) == value)
        if filters.deadline_from is not None:
            query = query.where(Activity.deadline >= filters.deadline_from)
        if filters.deadline_to is not None:
            query = query.where(Activity.deadline <= filters.deadline_to)
        if filters.after_id is not None:
            query = query.where(Activity.id > filters.after_id)
        rows = self._db.scalars(
            query.order_by(Activity.id).limit(filters.limit + 1)
        ).all()
        items = [ActivityResponse.model_validate(r) for r in rows[: filters.limit]]
        return ActivityListResponse(
            items=items,
            next_after_id=items[-1].id if len(rows) > filters.limit else None,
        )

    def history(
        self, user_id: int, activity_id: int, limit: int, after_revision: int | None
    ) -> ActivityHistoryResponse:
        self._owned(user_id, activity_id)
        # The join makes ownership explicit in the history query as well.
        query = (
            select(ActivityDeadlineEvent)
            .join(Activity, Activity.id == ActivityDeadlineEvent.activity_id)
            .where(Activity.id == activity_id, Activity.user_id == user_id)
        )
        if after_revision is not None:
            query = query.where(ActivityDeadlineEvent.revision > after_revision)
        rows = self._db.scalars(
            query.order_by(ActivityDeadlineEvent.revision).limit(limit + 1)
        ).all()
        items = [ActivityDeadlineEventResponse.model_validate(r) for r in rows[:limit]]
        return ActivityHistoryResponse(
            items=items,
            next_after_revision=items[-1].revision if len(rows) > limit else None,
        )

    def _write(
        self, user_id: int, operation: Callable[[], T], *, deleting: bool = False
    ) -> T:
        self._db.rollback()  # End authentication/onboarding read snapshot.
        for attempt in range(3):
            try:
                self._db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                owner = self._db.scalar(
                    select(User.id).where(User.id == user_id).with_for_update()
                )
                if owner is None:
                    raise DomainError("ACTIVITY_NOT_FOUND")
                result = operation()
                self._db.commit()
                return result
            except DBAPIError as exc:
                self._db.rollback()
                state = getattr(exc.orig, "sqlstate", None)
                constraint = getattr(
                    getattr(exc.orig, "diag", None), "constraint_name", None
                )
                if state in {"23503", "23001"}:
                    if deleting:
                        raise DomainError("ACTIVITY_HAS_DEPENDENCIES") from None
                    if constraint == "fk_activities_owner_subject":
                        raise DomainError("SUBJECT_NOT_FOUND") from None
                if state not in {"40001", "40P01"}:
                    raise
                if attempt == 2:
                    raise DomainError("ACTIVITY_WRITE_CONFLICT") from None
                time.sleep(0.01 * (attempt + 1))
            except Exception:
                self._db.rollback()
                raise
        raise AssertionError("unreachable")

    def _response(self, record: Activity) -> ActivityResponse:
        self._db.flush()
        self._db.refresh(
            record
        )  # Read trigger-owned original date/revision/timestamps.
        return ActivityResponse.model_validate(record)

    def create(self, user_id: int, data: ActivityWrite) -> ActivityResponse:
        def insert() -> ActivityResponse:
            self._subject(user_id, data.subject_id)
            record = Activity(user_id=user_id, **data.model_dump())
            self._db.add(record)
            return self._response(record)

        return self._write(user_id, insert)

    def update(
        self, user_id: int, activity_id: int, data: ActivityWrite
    ) -> ActivityResponse:
        def replace() -> ActivityResponse:
            record = self._owned(user_id, activity_id, lock=True)
            self._subject(user_id, data.subject_id)
            validate_transition(record.status, data.status)
            for key, value in data.model_dump().items():
                setattr(record, key, value)
            return self._response(record)

        return self._write(user_id, replace)

    def set_status(
        self, user_id: int, activity_id: int, data: ActivityStatusRequest
    ) -> ActivityResponse:
        def transition() -> ActivityResponse:
            record = self._owned(user_id, activity_id, lock=True)
            if record.status != data.expected_status:
                raise DomainError("ACTIVITY_STATE_CONFLICT")
            validate_transition(record.status, data.status)
            record.status = data.status
            return self._response(record)

        return self._write(user_id, transition)

    def set_deadline(
        self, user_id: int, activity_id: int, data: ActivityDeadlineRequest
    ) -> ActivityResponse:
        def reschedule() -> ActivityResponse:
            record = self._owned(user_id, activity_id, lock=True)
            if record.deadline_revision != data.expected_revision:
                raise DomainError("ACTIVITY_DEADLINE_CONFLICT")
            record.deadline = data.deadline
            return self._response(record)

        return self._write(user_id, reschedule)

    def delete(self, user_id: int, activity_id: int) -> None:
        def remove() -> None:
            self._db.delete(self._owned(user_id, activity_id, lock=True))
            self._db.flush()

        self._write(user_id, remove, deleting=True)
