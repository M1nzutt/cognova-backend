from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    FetchedValue,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class StudySession(Base):
    """Read/write mapping of external 0006; never used to create schema."""

    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    subject_id: Mapped[int] = mapped_column(Integer)
    activity_id: Mapped[int | None] = mapped_column(Integer)
    planned_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    planned_duration: Mapped[int] = mapped_column(SmallInteger)
    execution_state: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'planned'::text")
    )
    status: Mapped[str | None] = mapped_column(Text)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_duration: Mapped[Decimal] = mapped_column(
        Numeric(20, 6), nullable=False, server_default=text("0")
    )
    context: Mapped[str | None] = mapped_column(Text)
    other_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        server_onupdate=FetchedValue(),
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "subject_id"],
            ["subjects.user_id", "subjects.id"],
            name="fk_study_sessions_owner_subject",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["user_id", "subject_id", "activity_id"],
            ["activities.user_id", "activities.subject_id", "activities.id"],
            name="fk_study_sessions_owner_subject_activity",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        UniqueConstraint(
            "user_id",
            "subject_id",
            "id",
            name="uq_study_sessions_user_subject_id",
        ),
        UniqueConstraint(
            "user_id",
            "subject_id",
            "activity_id",
            "id",
            name="uq_study_sessions_user_subject_activity_id",
        ),
        CheckConstraint(
            "isfinite(planned_start_at)", name="ck_study_sessions_planned_start"
        ),
        CheckConstraint(
            "planned_duration BETWEEN 10 AND 180",
            name="ck_study_sessions_planned_duration",
        ),
        CheckConstraint(
            "execution_state IN ('planned','running','paused','finished')",
            name="ck_study_sessions_execution_state",
        ),
        CheckConstraint(
            "status IN ('completed','partial','postponed','cancelled')",
            name="ck_study_sessions_status",
        ),
        CheckConstraint(
            "(start_at IS NULL OR isfinite(start_at)) AND "
            "(end_at IS NULL OR (isfinite(end_at) AND start_at IS NOT NULL "
            "AND end_at > start_at))",
            name="ck_study_sessions_execution_times",
        ),
        CheckConstraint(
            "actual_duration >= 0 AND actual_duration < 'Infinity'::numeric",
            name="ck_study_sessions_actual_duration",
        ),
        CheckConstraint(
            "context IN ('finished_early','distracted','tired','interrupted',"
            "'changed_activity','other')",
            name="ck_study_sessions_context",
        ),
        CheckConstraint(
            "(context IS NOT DISTINCT FROM 'other' AND other_text IS NOT NULL "
            "AND char_length(other_text) BETWEEN 1 AND 200 "
            "AND other_text = btrim(other_text) "
            "AND other_text !~ '^[[:space:]]*$') OR "
            "(context IS DISTINCT FROM 'other' AND other_text IS NULL)",
            name="ck_study_sessions_other_text",
        ),
        CheckConstraint(
            "(execution_state = 'planned' AND start_at IS NULL "
            "AND end_at IS NULL AND actual_duration = 0 AND status IS NULL "
            "AND context IS NULL) OR "
            "(execution_state IN ('running','paused') AND start_at IS NOT NULL "
            "AND end_at IS NULL AND status IS NULL AND context IS NULL) OR "
            "(execution_state = 'finished' AND status IS NOT NULL AND ("
            "(start_at IS NOT NULL AND end_at IS NOT NULL AND actual_duration > 0) "
            "OR (status IN ('postponed','cancelled') AND start_at IS NULL "
            "AND end_at IS NULL AND actual_duration = 0)))",
            name="ck_study_sessions_lifecycle",
        ),
        CheckConstraint(
            "isfinite(created_at) AND isfinite(updated_at) "
            "AND updated_at >= created_at",
            name="ck_study_sessions_timestamps",
        ),
        Index(
            "ix_study_sessions_user_planned",
            "user_id",
            "planned_start_at",
            "id",
        ),
        Index(
            "ix_study_sessions_owner_activity", "user_id", "subject_id", "activity_id"
        ),
        Index(
            "uq_study_sessions_user_executing",
            "user_id",
            unique=True,
            postgresql_where=text("execution_state IN ('running','paused')"),
        ),
    )


__all__ = ["StudySession"]
