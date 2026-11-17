from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.academic_chat import AcademicConversation, AcademicMessage


class AcademicChatRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_conversation(self, user_id: int) -> AcademicConversation:
        conversation = AcademicConversation(user_id=user_id, title="Nueva conversación")
        self._db.add(conversation)
        self._db.flush()
        self._db.commit()
        self._db.refresh(conversation)
        return conversation

    def list_conversations(self, user_id: int) -> list[AcademicConversation]:
        return list(
            self._db.scalars(
                select(AcademicConversation)
                .where(AcademicConversation.user_id == user_id)
                .order_by(
                    AcademicConversation.updated_at.desc(),
                    AcademicConversation.id.desc(),
                )
                .limit(50)
            )
        )

    def conversation(
        self, user_id: int, conversation_id: int
    ) -> AcademicConversation | None:
        return self._db.scalar(
            select(AcademicConversation).where(
                AcademicConversation.user_id == user_id,
                AcademicConversation.id == conversation_id,
            )
        )

    def conversation_count(self, user_id: int) -> int:
        return int(
            self._db.scalar(
                select(func.count())
                .select_from(AcademicConversation)
                .where(AcademicConversation.user_id == user_id)
            )
            or 0
        )

    def messages(
        self, user_id: int, conversation_id: int, before_id: int | None, limit: int
    ) -> list[AcademicMessage]:
        query = select(AcademicMessage).where(
            AcademicMessage.user_id == user_id,
            AcademicMessage.conversation_id == conversation_id,
        )
        if before_id is not None:
            query = query.where(AcademicMessage.id < before_id)
        return list(
            self._db.scalars(
                query.order_by(AcademicMessage.id.desc()).limit(limit + 1)
            )
        )

    def message_count(self, user_id: int, conversation_id: int) -> int:
        return int(
            self._db.scalar(
                select(func.count())
                .select_from(AcademicMessage)
                .where(
                    AcademicMessage.user_id == user_id,
                    AcademicMessage.conversation_id == conversation_id,
                )
            )
            or 0
        )

    def add_user_message(
        self,
        conversation: AcademicConversation,
        content: str,
    ) -> AcademicMessage:
        message = AcademicMessage(
            user_id=conversation.user_id,
            conversation_id=conversation.id,
            role="user",
            content=content,
            evidence=[],
        )
        self._db.add(message)
        if self.message_count(conversation.user_id, conversation.id) == 0:
            conversation.title = content[:80].strip() or "Nueva conversación"
        conversation.updated_at = datetime.now(timezone.utc)
        self._db.flush()
        self._db.commit()
        self._db.refresh(message)
        self._db.refresh(conversation)
        return message

    def add_assistant_message(
        self,
        conversation: AcademicConversation,
        content: str,
        evidence: list[str],
    ) -> AcademicMessage:
        message = AcademicMessage(
            user_id=conversation.user_id,
            conversation_id=conversation.id,
            role="assistant",
            content=content,
            evidence=evidence,
        )
        self._db.add(message)
        conversation.updated_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(message)
        self._db.refresh(conversation)
        return message
