from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.api.onboarding_dependencies import get_onboarded_user
from app.database.dependencies import get_session
from app.models.user import User
from app.schemas.activity_deadline_request import ActivityDeadlineRequest
from app.schemas.activity_filters import ActivityFilters
from app.schemas.activity_history_response import ActivityHistoryResponse
from app.schemas.activity_list_response import ActivityListResponse
from app.schemas.activity_response import ActivityResponse
from app.schemas.activity_status_request import ActivityStatusRequest
from app.schemas.activity_write import ActivityWrite
from app.schemas.error_response import ErrorResponse
from app.services.activity_service import ActivityService

router = APIRouter(
    prefix="/activities",
    tags=["activities"],
    responses={c: {"model": ErrorResponse} for c in (401, 403, 404, 409, 422, 503)},
)
CurrentUser = Annotated[User, Depends(get_onboarded_user)]
ActivityId = Annotated[int, Path(gt=0, le=2147483647)]


def get_service(db: Annotated[Session, Depends(get_session)]) -> ActivityService:
    return ActivityService(db)


Service = Annotated[ActivityService, Depends(get_service)]


@router.post("", status_code=201, response_model=ActivityResponse)
def create(
    data: ActivityWrite, user: CurrentUser, service: Service
) -> ActivityResponse:
    return service.create(user.id, data)


@router.get("", response_model=ActivityListResponse)
def list_activities(
    user: CurrentUser, service: Service, filters: Annotated[ActivityFilters, Query()]
) -> ActivityListResponse:
    return service.list(user.id, filters)


@router.get("/{activity_id}", response_model=ActivityResponse)
def detail(
    activity_id: ActivityId, user: CurrentUser, service: Service
) -> ActivityResponse:
    return service.detail(user.id, activity_id)


@router.put("/{activity_id}", response_model=ActivityResponse)
def update(
    activity_id: ActivityId, data: ActivityWrite, user: CurrentUser, service: Service
) -> ActivityResponse:
    return service.update(user.id, activity_id, data)


@router.patch("/{activity_id}/status", response_model=ActivityResponse)
def change_status(
    activity_id: ActivityId,
    data: ActivityStatusRequest,
    user: CurrentUser,
    service: Service,
) -> ActivityResponse:
    return service.set_status(user.id, activity_id, data)


@router.patch("/{activity_id}/deadline", response_model=ActivityResponse)
def change_deadline(
    activity_id: ActivityId,
    data: ActivityDeadlineRequest,
    user: CurrentUser,
    service: Service,
) -> ActivityResponse:
    return service.set_deadline(user.id, activity_id, data)


@router.get("/{activity_id}/deadline-history", response_model=ActivityHistoryResponse)
def history(
    activity_id: ActivityId,
    user: CurrentUser,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    after_revision: Annotated[int | None, Query(gt=0, le=2147483647)] = None,
) -> ActivityHistoryResponse:
    return service.history(user.id, activity_id, limit, after_revision)


@router.delete("/{activity_id}", status_code=204)
def delete(
    activity_id: ActivityId,
    user: CurrentUser,
    service: Service,
    confirm: Annotated[
        Literal["true"], Query(description="Explicit irreversible deletion")
    ],
) -> Response:
    service.delete(user.id, activity_id)
    return Response(status_code=204)
