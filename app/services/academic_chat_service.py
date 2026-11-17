import json
from typing import Any

from sqlalchemy.orm import Session

from app.academic_intelligence.academic_context import AcademicContext
from app.academic_intelligence.gemini_provider import GeminiProvider
from app.core.domain_error import DomainError
from app.models.academic_chat import AcademicConversation, AcademicMessage
from app.repositories.academic_chat_repository import AcademicChatRepository
from app.schemas.academic_chat import (
    AcademicChatSendResponse,
    AcademicConversationListResponse,
    AcademicConversationResponse,
    AcademicMessagePageResponse,
    AcademicMessageResponse,
)

MAX_CONVERSATIONS_PER_USER = 50
MAX_MESSAGES_PER_CONVERSATION = 200
MAX_HISTORY_MESSAGES = 12
MAX_HISTORY_CHARS = 8000
MAX_MODEL_CONTEXT_BYTES = 24000


class AcademicChatService:
    def __init__(self, db: Session, provider: GeminiProvider) -> None:
        self._db = db
        self._repository = AcademicChatRepository(db)
        self._provider = provider

    def create(self, user_id: int) -> AcademicConversationResponse:
        if self._repository.conversation_count(user_id) >= MAX_CONVERSATIONS_PER_USER:
            raise DomainError("ACADEMIC_CONVERSATION_LIMIT")
        return AcademicConversationResponse.model_validate(
            self._repository.create_conversation(user_id)
        )

    def list_conversations(self, user_id: int) -> AcademicConversationListResponse:
        return AcademicConversationListResponse(
            items=[
                AcademicConversationResponse.model_validate(row)
                for row in self._repository.list_conversations(user_id)
            ]
        )

    def messages(
        self,
        user_id: int,
        conversation_id: int,
        before_id: int | None,
        limit: int,
    ) -> AcademicMessagePageResponse:
        if self._owned_conversation(user_id, conversation_id) is None:
            raise DomainError("ACADEMIC_CONVERSATION_NOT_FOUND")
        rows = self._repository.messages(user_id, conversation_id, before_id, limit)
        has_more = len(rows) > limit
        page = rows[:limit]
        page.reverse()
        return AcademicMessagePageResponse(
            items=[self._message(row) for row in page],
            next_before_id=page[0].id if has_more and page else None,
        )

    def send(
        self, user_id: int, conversation_id: int, content: str
    ) -> AcademicChatSendResponse:
        conversation = self._owned_conversation(user_id, conversation_id)
        if conversation is None:
            raise DomainError("ACADEMIC_CONVERSATION_NOT_FOUND")
        if (
            self._repository.message_count(user_id, conversation_id)
            >= MAX_MESSAGES_PER_CONVERSATION
        ):
            raise DomainError("ACADEMIC_CONVERSATION_FULL")

        user_message = self._repository.add_user_message(conversation, content)
        academic_context = AcademicContext(self._db, user_id)
        evidence_catalog = academic_context.evidence_catalog
        context_json = self._build_context(
            academic_context.as_json(),
            self._repository.messages(
                user_id, conversation_id, before_id=None, limit=MAX_HISTORY_MESSAGES
            ),
        )
        self._db.rollback()

        reply = self._provider.academic_chat(context_json)
        keys = reply.evidence_keys
        if (
            len(set(keys)) != len(keys)
            or not set(keys).issubset(evidence_catalog)
            or len(keys) > 8
        ):
            raise DomainError("ACADEMIC_CHAT_UNAVAILABLE")
        evidence = [evidence_catalog[key] for key in keys]
        assistant_message = self._repository.add_assistant_message(
            conversation, reply.answer.strip(), evidence
        )
        return AcademicChatSendResponse(
            conversation=AcademicConversationResponse.model_validate(conversation),
            user_message=self._message(user_message),
            assistant_message=self._message(assistant_message),
        )

    def _owned_conversation(
        self, user_id: int, conversation_id: int
    ) -> AcademicConversation | None:
        return self._repository.conversation(user_id, conversation_id)

    @staticmethod
    def _message(row: AcademicMessage) -> AcademicMessageResponse:
        return AcademicMessageResponse.model_validate(row)

    @classmethod
    def _build_context(cls, academic_json: str, messages: list[AcademicMessage]) -> str:
        source: dict[str, Any] = json.loads(academic_json)
        subject_rows = source.get("subjects", [])[:50]
        activity_rows = source.get("activities", [])[:24]
        session_rows = source.get("sessions", [])[:16]
        included_keys = {
            *(f"subject:{row['id']}" for row in subject_rows),
            *(f"activity:{row['id']}" for row in activity_rows),
            *(f"session:{row['id']}" for row in session_rows),
        }
        academic = {
            "evidence_catalog": {
                key: value
                for key, value in source.get("evidence_catalog", {}).items()
                if key in included_keys
            },
            "questionnaire_answers": source.get("questionnaire_answers", {}),
            "subjects": subject_rows,
            "activities": activity_rows,
            "sessions": session_rows,
            "previous_plans": source.get("previous_plans", [])[:8],
            "previous_challenges": source.get("previous_challenges", [])[:12],
            "user_decisions": source.get("user_decisions", [])[:12],
            "finished_valid_sessions": source.get("finished_valid_sessions", 0),
            "nearby_schedule": source.get("nearby_schedule", [])[:16],
        }
        history: list[dict[str, str]] = [
            {"role": row.role, "content": row.content}
            for row in reversed(messages)
        ][-MAX_HISTORY_MESSAGES:]
        while (
            history
            and sum(len(row["content"]) for row in history) > MAX_HISTORY_CHARS
        ):
            history.pop(0)

        while True:
            payload = json.dumps(
                {"academic_context": academic, "recent_conversation": history},
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if len(payload.encode("utf-8")) <= MAX_MODEL_CONTEXT_BYTES:
                return payload
            for rows in (
                academic["activities"],
                academic["sessions"],
                academic["nearby_schedule"],
                academic["previous_challenges"],
                academic["user_decisions"],
            ):
                if rows:
                    rows.pop()
                    break
            else:
                if len(history) > 1:
                    history.pop(0)
                elif academic["questionnaire_answers"]:
                    academic["questionnaire_answers"] = {}
                elif academic["subjects"]:
                    removed = academic["subjects"].pop()
                    academic["evidence_catalog"].pop(f"subject:{removed['id']}", None)
                elif academic["evidence_catalog"]:
                    academic["evidence_catalog"].pop(next(iter(academic["evidence_catalog"])))
                else:
                    raise DomainError("ACADEMIC_CHAT_UNAVAILABLE")
