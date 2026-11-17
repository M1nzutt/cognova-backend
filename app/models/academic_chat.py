from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AcademicConversation(Base):
    __tablename__ = "academic_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_academic_conversations_user",
            ondelete="CASCADE",
        ),
        UniqueConstraint("user_id", "id", name="uq_academic_conversations_user_id_id"),
        CheckConstraint(
            "char_length(title) BETWEEN 1 AND 80 AND title = btrim(title) "
            "AND title !~ '^[[:space:]]*$'",
            name="ck_academic_conversations_title",
        ),
        CheckConstraint(
            "isfinite(created_at) AND isfinite(updated_at) "
            "AND updated_at >= created_at",
            name="ck_academic_conversations_timestamps",
        ),
        Index(
            "ix_academic_conversations_user_updated", "user_id", "updated_at", "id"
        ),
    )


class AcademicMessage(Base):
    __tablename__ = "academic_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    conversation_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "conversation_id"],
            ["academic_conversations.user_id", "academic_conversations.id"],
            name="fk_academic_messages_owner_conversation",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "role IN ('user','assistant')", name="ck_academic_messages_role"
        ),
        CheckConstraint(
            "(role = 'user' AND char_length(content) BETWEEN 1 AND 4000 "
            "AND jsonb_typeof(evidence) = 'array' AND evidence = '[]'::jsonb) OR "
            "(role = 'assistant' AND char_length(content) BETWEEN 1 AND 3000 "
            "AND jsonb_typeof(evidence) = 'array' "
            "AND octet_length(evidence::text) <= 8192)",
            name="ck_academic_messages_content_evidence",
        ),
        CheckConstraint(
            "isfinite(created_at)", name="ck_academic_messages_created_at"
        ),
        Index(
            "ix_academic_messages_user_conversation_id",
            "user_id",
            "conversation_id",
            "id",
        ),
    )


__all__ = ["AcademicConversation", "AcademicMessage"]
