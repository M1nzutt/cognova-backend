from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ActivityDeadlineEvent(Base):
    """Read-only application mapping; only the database trigger writes events."""

    __tablename__ = "activity_deadline_events"
    activity_id: Mapped[int] = mapped_column(
        ForeignKey(
            "activities.id",
            name="fk_deadline_events_activity",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        primary_key=True,
    )
    revision: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False
    )
    previous_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    new_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event_type: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("revision > 0", name="ck_deadline_events_revision"),
        CheckConstraint(
            "isfinite(previous_deadline) AND isfinite(new_deadline) "
            "AND isfinite(occurred_at)",
            name="ck_deadline_events_finite",
        ),
        CheckConstraint(
            "(event_type = 'postponed' AND new_deadline > previous_deadline) "
            "OR (event_type = 'rescheduled' AND new_deadline < previous_deadline)",
            name="ck_deadline_events_direction",
        ),
    )
