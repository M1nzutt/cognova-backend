import os
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.academic_intelligence.gemini_provider import GeminiProvider
from app.api.onboarding_dependencies import get_onboarded_user
from app.core.auth_error import AuthError
from app.core.domain_error import DomainError
from app.database.dependencies import get_session
from app.models.user import User
from app.schemas.academic_chat import (
    AcademicChatMessageWrite,
    AcademicChatSendResponse,
    AcademicConversationListResponse,
    AcademicConversationResponse,
    AcademicMessagePageResponse,
)
from app.schemas.error_response import ErrorResponse
from app.services.academic_chat_service import AcademicChatService

router = APIRouter(
    prefix="/academic-chat",
    tags=["academic-chat"],
    responses={
        code: {"model": ErrorResponse}
        for code in (401, 403, 404, 409, 422, 429, 503)
    },
)
CurrentUser = Annotated[User, Depends(get_onboarded_user)]
ConversationId = Annotated[int, Path(gt=0, le=2147483647)]


def get_chat_service(
    db: Annotated[Session, Depends(get_session)],
    request: Request,
) -> AcademicChatService:
    provider = GeminiProvider(
        os.environ.get("GEMINI_API_KEY"),
        request_id=getattr(request.state, "request_id", None),
        model=request.app.state.settings.gemini_model,
        timeout_ms=request.app.state.settings.gemini_timeout_ms,
    )
    return AcademicChatService(db, provider)


ChatService = Annotated[AcademicChatService, Depends(get_chat_service)]


@router.get("/conversations", response_model=AcademicConversationListResponse)
def list_conversations(user: CurrentUser, service: ChatService):
    return service.list_conversations(user.id)


@router.post(
    "/conversations",
    status_code=status.HTTP_201_CREATED,
    response_model=AcademicConversationResponse,
)
def create_conversation(user: CurrentUser, service: ChatService):
    return service.create(user.id)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=AcademicMessagePageResponse,
)
def list_messages(
    conversation_id: ConversationId,
    user: CurrentUser,
    service: ChatService,
    before_id: Annotated[int | None, Query(gt=0, le=2147483647)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    return service.messages(user.id, conversation_id, before_id, limit)


@router.post(
    "/conversations/{conversation_id}/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=AcademicChatSendResponse,
)
def send_message(
    conversation_id: ConversationId,
    data: AcademicChatMessageWrite,
    user: CurrentUser,
    service: ChatService,
    request: Request,
):
    limiter = request.app.state.rate_limiter
    if limiter is None:
        raise DomainError("ACADEMIC_CHAT_UNAVAILABLE")
    try:
        limiter.check("gemini-academic-chat", str(user.id))
    except AuthError as exc:
        if exc.code != "TOO_MANY_REQUESTS":
            raise
        raise DomainError("ACADEMIC_CHAT_LIMIT") from None
    return service.send(user.id, conversation_id, data.content)
