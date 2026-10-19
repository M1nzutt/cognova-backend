import time
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.domain_error import DomainError
from app.models.subject import Subject
from app.models.user import User
from app.schemas.subject_create import SubjectCreate
from app.schemas.subject_list_response import SubjectListResponse
from app.schemas.subject_response import SubjectResponse
from app.schemas.subject_write import SubjectWrite

T = TypeVar("T")


class SubjectService:
    """Own a complete mutation transaction; request session has no pending writes."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def _owned(self, user_id: int, subject_id: int) -> Subject:
        record = self._db.scalar(
            select(Subject)
            .where(Subject.id == subject_id, Subject.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        if record is None:
            raise DomainError("SUBJECT_NOT_FOUND")
        return record

    def detail(self, user_id: int, subject_id: int) -> SubjectResponse:
        return SubjectResponse.model_validate(self._owned(user_id, subject_id))

    def list(
        self, user_id: int, status: str, limit: int, after_id: int | None
    ) -> SubjectListResponse:
        query = select(Subject).where(Subject.user_id == user_id)
        if status != "all":
            query = query.where(Subject.status == status)
        if after_id is not None:
            query = query.where(Subject.id > after_id)
        records = self._db.scalars(query.order_by(Subject.id).limit(limit + 1)).all()
        items = [SubjectResponse.model_validate(row) for row in records[:limit]]
        return SubjectListResponse(
            items=items, next_after_id=items[-1].id if len(records) > limit else None
        )

    def _slot(self, user_id: int, *, reactivating: bool = False) -> int:
        occupied = set(
            self._db.scalars(
                select(Subject.active_slot).where(
                    Subject.user_id == user_id, Subject.status == "active"
                )
            )
        )
        for slot in range(1, 6):
            if slot not in occupied:
                return slot
        raise DomainError(
            "SUBJECT_REACTIVATION_LIMIT" if reactivating else "SUBJECT_ACTIVE_LIMIT"
        )

    def _write(
        self, user_id: int, operation: Callable[[], T], *, deleting: bool = False
    ) -> T:
        for attempt in range(3):
            try:
                owner = self._db.scalar(
                    select(User.id).where(User.id == user_id).with_for_update()
                )
                if owner is None:
                    raise DomainError("SUBJECT_NOT_FOUND")
                result = operation()
                self._db.commit()
                return result
            except DBAPIError as exc:
                self._db.rollback()
                state = getattr(exc.orig, "sqlstate", None)
                constraint = getattr(
                    getattr(exc.orig, "diag", None), "constraint_name", None
                )
                if state == "23505" and constraint == "uq_subjects_user_name_lower":
                    raise DomainError("SUBJECT_NAME_CONFLICT") from None
                if state == "23503" and deleting:
                    raise DomainError("SUBJECT_HAS_DEPENDENCIES") from None
                retry = state in {"40001", "40P01"} or (
                    state == "23505" and constraint == "uq_subjects_active_slot"
                )
                if not retry:
                    raise
                if attempt == 2:
                    raise DomainError("SUBJECT_WRITE_CONFLICT") from None
                time.sleep(0.01 * (attempt + 1))
            except Exception:
                self._db.rollback()
                raise
        raise AssertionError("unreachable")

    def _response(self, record: Subject) -> SubjectResponse:
        self._db.flush()
        self._db.refresh(record)
        return SubjectResponse.model_validate(record)

    def create(self, user_id: int, data: SubjectCreate) -> SubjectResponse:
        def insert_record() -> SubjectResponse:
            record = Subject(
                user_id=user_id,
                **data.model_dump(),
                active_slot=self._slot(user_id) if data.status == "active" else None,
            )
            self._db.add(record)
            return self._response(record)

        return self._write(user_id, insert_record)

    def update(
        self, user_id: int, subject_id: int, data: SubjectWrite
    ) -> SubjectResponse:
        def update_record() -> SubjectResponse:
            record = self._owned(user_id, subject_id)
            for key, value in data.model_dump().items():
                setattr(record, key, value)
            return self._response(record)

        return self._write(user_id, update_record)

    def set_archived(
        self, user_id: int, subject_id: int, *, archived: bool
    ) -> SubjectResponse:
        def transition() -> SubjectResponse:
            record = self._owned(user_id, subject_id)
            status = "archived" if archived else "active"
            if record.status != status:
                record.active_slot = (
                    None if archived else self._slot(user_id, reactivating=True)
                )
                record.status = status
            return self._response(record)

        return self._write(user_id, transition)

    def delete(self, user_id: int, subject_id: int) -> None:
        def delete_record() -> None:
            self._db.delete(self._owned(user_id, subject_id))
            self._db.flush()

        self._write(user_id, delete_record, deleting=True)
