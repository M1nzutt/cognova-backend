from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    FetchedValue,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Activity(Base):
    """Read/write mapping of external 0005; metadata never creates schema."""

    __tablename__ = "activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    subject_id: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    original_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=FetchedValue()
    )
    deadline_revision: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), server_onupdate=FetchedValue()
    )
    priority: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    estimated_duration: Mapped[int] = mapped_column(SmallInteger)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=FetchedValue(),
    )
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "subject_id"],
            ["subjects.user_id", "subjects.id"],
            name="fk_activities_owner_subject",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        CheckConstraint(
            "char_length(title) BETWEEN 1 AND 50 "
            "AND title = btrim(title) AND title !~ '^[[:space:]]*$'",
            name="ck_activities_title",
        ),
        CheckConstraint("isfinite(deadline)", name="ck_activities_deadline"),
        CheckConstraint(
            "isfinite(original_deadline)", name="ck_activities_original_deadline"
        ),
        CheckConstraint("deadline_revision >= 0", name="ck_activities_revision"),
        CheckConstraint(
            "priority IN ('low','medium','high','urgent')",
            name="ck_activities_priority",
        ),
        CheckConstraint(
            "status IN ('pending','in_progress','completed','postponed','cancelled')",
            name="ck_activities_status",
        ),
        CheckConstraint(
            "estimated_duration BETWEEN 10 AND 300", name="ck_activities_duration"
        ),
        CheckConstraint("char_length(notes) <= 200", name="ck_activities_notes"),
        CheckConstraint(
            "isfinite(created_at) AND isfinite(updated_at) "
            "AND updated_at >= created_at",
            name="ck_activities_timestamps",
        ),
        Index("ix_activities_user_subject", "user_id", "subject_id"),
        Index(
            "ix_activities_user_status_deadline", "user_id", "status", "deadline", "id"
        ),
    )
