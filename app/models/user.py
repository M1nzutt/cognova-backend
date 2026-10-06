from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class User(Base):
    """An account; password hashes are never part of public schemas."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    degree_program: Mapped[str] = mapped_column(Text)
    semester: Mapped[int] = mapped_column(Integer)
    academic_goal: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("uq_users_email_lower", func.lower(email), unique=True),
        CheckConstraint("semester > 0", name="ck_users_semester_positive"),
    )
