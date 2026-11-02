from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.api.onboarding_dependencies import get_onboarded_user
from app.database.dependencies import get_session
from app.models.user import User
from app.schemas.error_response import ErrorResponse
from app.schemas.study_session_detail import StudySessionDetail
from app.schemas.study_session_filters import StudySessionFilters
from app.schemas.study_session_finish import StudySessionFinish
from app.schemas.study_session_list_response import StudySessionListResponse
from app.schemas.study_session_write import StudySessionWrite
from app.services.study_session_service import StudySessionService

router = APIRouter(
    prefix="/sessions",
    tags=["study-sessions"],
    responses={
        code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 503)
    },
)
CurrentUser = Annotated[User, Depends(get_onboarded_user)]
SessionId = Annotated[int, Path(gt=0, le=2147483647)]


def get_service(db: Annotated[Session, Depends(get_session)]) -> StudySessionService:
    return StudySessionService(db)


Service = Annotated[StudySessionService, Depends(get_service)]


@router.get("", response_model=StudySessionListResponse)
def list_sessions(
    user: CurrentUser,
    service: Service,
    filters: Annotated[StudySessionFilters, Query()],
) -> StudySessionListResponse:
    return service.list(user.id, filters)


@router.post("", status_code=201, response_model=StudySessionDetail)
def create(
    data: StudySessionWrite, user: CurrentUser, service: Service
) -> StudySessionDetail:
    return service.create(user.id, data)


@router.get("/{session_id}", response_model=StudySessionDetail)
def detail(
    session_id: SessionId, user: CurrentUser, service: Service
) -> StudySessionDetail:
    return service.detail(user.id, session_id)


@router.put("/{session_id}", response_model=StudySessionDetail)
def update(
    session_id: SessionId,
    data: StudySessionWrite,
    user: CurrentUser,
    service: Service,
) -> StudySessionDetail:
    return service.update(user.id, session_id, data)


@router.delete("/{session_id}", status_code=204)
def delete(
    session_id: SessionId,
    user: CurrentUser,
    service: Service,
    confirm: Annotated[
        Literal["true"], Query(description="Confirm deletion of an unstarted plan")
    ],
) -> Response:
    service.delete(user.id, session_id)
    return Response(status_code=204)


@router.post("/{session_id}/start", response_model=StudySessionDetail)
def start(
    session_id: SessionId, user: CurrentUser, service: Service
) -> StudySessionDetail:
    return service.start(user.id, session_id)


@router.post("/{session_id}/pause", response_model=StudySessionDetail)
def pause(
    session_id: SessionId, user: CurrentUser, service: Service
) -> StudySessionDetail:
    return service.pause(user.id, session_id)


@router.post("/{session_id}/resume", response_model=StudySessionDetail)
def resume(
    session_id: SessionId, user: CurrentUser, service: Service
) -> StudySessionDetail:
    return service.resume(user.id, session_id)


@router.post("/{session_id}/finish", response_model=StudySessionDetail)
def finish(
    session_id: SessionId,
    data: StudySessionFinish,
    user: CurrentUser,
    service: Service,
) -> StudySessionDetail:
    return service.finish(user.id, session_id, data)
