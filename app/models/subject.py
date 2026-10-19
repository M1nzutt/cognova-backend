from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Subject(Base):
    """Query mapping for external 0004; never used to create schema."""

    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_subjects_user_id_users", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(Text)
    color_base: Mapped[str] = mapped_column(Text)
    color_shade: Mapped[int] = mapped_column(SmallInteger)
    active_slot: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "char_length(name) BETWEEN 1 AND 20 AND name = btrim(name) "
            "AND name !~ '^[[:space:]]*$'",
            name="ck_subjects_name",
        ),
        CheckConstraint("status IN ('active', 'archived')", name="ck_subjects_status"),
        CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard')", name="ck_subjects_difficulty"
        ),
        CheckConstraint(
            "color_base ~ '^[a-z][a-z0-9_-]{0,31}$'", name="ck_subjects_color_base"
        ),
        CheckConstraint(
            "color_shade BETWEEN 0 AND 1000", name="ck_subjects_color_shade"
        ),
        CheckConstraint(
            "(status = 'active' AND active_slot IS NOT NULL "
            "AND active_slot BETWEEN 1 AND 5) "
            "OR (status = 'archived' AND active_slot IS NULL)",
            name="ck_subjects_active_slot",
        ),
        UniqueConstraint("user_id", "active_slot", name="uq_subjects_active_slot"),
        Index("uq_subjects_user_name_lower", "user_id", func.lower(name), unique=True),
        Index("ix_subjects_user_status", "user_id", "status"),
    )
