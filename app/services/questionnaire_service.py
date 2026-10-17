from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.domain_error import DomainError
from app.models.questionnaire_response import QuestionnaireResponseRecord
from app.models.user import User
from app.questionnaire.codec import decode_answers, encode_answers
from app.schemas.questionnaire_history_response import QuestionnaireHistoryResponse
from app.schemas.questionnaire_request import QuestionnaireRequest
from app.schemas.questionnaire_response import QuestionnaireResponse
from app.schemas.questionnaire_update_request import QuestionnaireUpdateRequest


class QuestionnaireService:
    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def response(record: QuestionnaireResponseRecord) -> QuestionnaireResponse:
        return QuestionnaireResponse(
            revision=record.revision,
            answers=decode_answers(record.answers, record.questionnaire_version),
            recorded_at=record.recorded_at,
        )

    def current(self, user_id: int) -> QuestionnaireResponse:
        record = self._db.scalar(
            select(QuestionnaireResponseRecord)
            .where(QuestionnaireResponseRecord.user_id == user_id)
            .order_by(QuestionnaireResponseRecord.revision.desc())
            .limit(1)
        )
        if record is None:
            raise DomainError("QUESTIONNAIRE_NOT_FOUND")
        return self.response(record)

    def _append(
        self, user_id: int, data: QuestionnaireRequest, expected: int
    ) -> QuestionnaireResponse:
        # Lock before reading the head: another transaction cannot append between
        # comparison and insert. PostgreSQL's trigger reinforces the same invariant.
        self._db.execute(
            select(User.id).where(User.id == user_id).with_for_update()
        ).scalar_one()
        latest = (
            self._db.scalar(
                select(func.max(QuestionnaireResponseRecord.revision)).where(
                    QuestionnaireResponseRecord.user_id == user_id
                )
            )
            or 0
        )
        if expected == 0 and latest != 0:
            raise DomainError("QUESTIONNAIRE_ALREADY_EXISTS")
        if expected > 0 and latest == 0:
            raise DomainError("QUESTIONNAIRE_NOT_FOUND")
        if latest != expected:
            raise DomainError("QUESTIONNAIRE_VERSION_CONFLICT")
        record = QuestionnaireResponseRecord(
            user_id=user_id,
            revision=latest + 1,
            questionnaire_version=data.questionnaire_version,
            answers=encode_answers(data.answers),
        )
        self._db.add(record)
        self._db.flush()
        self._db.refresh(record)
        result = self.response(record)
        self._db.commit()
        return result

    def create(self, user_id: int, data: QuestionnaireRequest) -> QuestionnaireResponse:
        return self._append(user_id, data, 0)

    def update(
        self, user_id: int, data: QuestionnaireUpdateRequest
    ) -> QuestionnaireResponse:
        return self._append(user_id, data, data.expected_revision)

    def history(
        self, user_id: int, limit: int, before_revision: int | None
    ) -> QuestionnaireHistoryResponse:
        query = select(QuestionnaireResponseRecord).where(
            QuestionnaireResponseRecord.user_id == user_id
        )
        if before_revision is not None:
            query = query.where(QuestionnaireResponseRecord.revision < before_revision)
        records = self._db.scalars(
            query.order_by(QuestionnaireResponseRecord.revision.desc()).limit(limit + 1)
        ).all()
        items = [self.response(record) for record in records[:limit]]
        return QuestionnaireHistoryResponse(
            items=items,
            next_before_revision=items[-1].revision if len(records) > limit else None,
        )
