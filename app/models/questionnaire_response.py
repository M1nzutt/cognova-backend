from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class QuestionnaireResponseRecord(Base):
    __tablename__ = "questionnaire_responses"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    questionnaire_version: Mapped[int] = mapped_column(Integer)
    answers: Mapped[dict[str, str | list[str]]] = mapped_column(JSONB)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    __table_args__ = (
        CheckConstraint("revision > 0", name="ck_questionnaire_revision_positive"),
        CheckConstraint(
            "questionnaire_version > 0", name="ck_questionnaire_version_positive"
        ),
        CheckConstraint(
            "cognova_valid_questionnaire_answers(answers)",
            name="ck_questionnaire_ten_answers",
        ),
    )
