from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    FetchedValue,
    ForeignKeyConstraint,
    Index,
    Integer,
    cast,
    func,
    literal_column,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class StudySessionInterval(Base):
    """Append-only execution evidence mapping of external 0006."""

    __tablename__ = "study_session_intervals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
            ["session_id"],
            ["study_sessions.id"],
            name="fk_study_intervals_session",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        CheckConstraint(
            "isfinite(started_at) AND "
            "(ended_at IS NULL OR (isfinite(ended_at) AND ended_at > started_at))",
            name="ck_study_intervals_times",
        ),
        CheckConstraint(
            "isfinite(created_at) AND isfinite(updated_at) "
            "AND updated_at >= created_at",
            name="ck_study_intervals_timestamps",
        ),
        Index("ix_study_intervals_session_started", "session_id", "started_at", "id"),
        Index(
            "uq_study_intervals_open",
            "session_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
        ExcludeConstraint(
            (
                func.int8range(
                    cast(literal_column("session_id"), BigInteger),
                    cast(literal_column("session_id"), BigInteger),
                    literal_column("'[]'"),
                ),
                "&&",
            ),
            (
                func.tstzrange(
                    literal_column("started_at"),
                    literal_column("ended_at"),
                    literal_column("'[)'"),
                ),
                "&&",
            ),
            name="ex_study_intervals_overlap",
            using="gist",
        ),
    )


__all__ = ["StudySessionInterval"]
