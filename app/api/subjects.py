from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.api.onboarding_dependencies import get_onboarded_user
from app.database.dependencies import get_session
from app.models.user import User
from app.schemas.error_response import ErrorResponse
from app.schemas.subject_catalog_response import SubjectCatalogResponse
from app.schemas.subject_create import SubjectCreate
from app.schemas.subject_list_response import SubjectListResponse
from app.schemas.subject_response import SubjectResponse
from app.schemas.subject_write import SubjectWrite
from app.services.subject_service import SubjectService

router = APIRouter(
    prefix="/subjects",
    tags=["subjects"],
    responses={c: {"model": ErrorResponse} for c in (401, 403, 404, 409, 422, 503)},
)
CurrentUser = Annotated[User, Depends(get_onboarded_user)]
SubjectId = Annotated[int, Path(gt=0, le=2147483647)]


def get_service(db: Annotated[Session, Depends(get_session)]) -> SubjectService:
    return SubjectService(db)


Service = Annotated[SubjectService, Depends(get_service)]


@router.get("/catalog", response_model=SubjectCatalogResponse)
def catalog(user: CurrentUser) -> SubjectCatalogResponse:
    return SubjectCatalogResponse()


@router.get("", response_model=SubjectListResponse)
def list_subjects(
    user: CurrentUser,
    service: Service,
    status: Literal["active", "archived", "all"] = "active",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    after_id: Annotated[int | None, Query(gt=0, le=2147483647)] = None,
) -> SubjectListResponse:
    return service.list(user.id, status, limit, after_id)


@router.post("", status_code=201, response_model=SubjectResponse)
def create(data: SubjectCreate, user: CurrentUser, service: Service) -> SubjectResponse:
    return service.create(user.id, data)


@router.get("/{subject_id}", response_model=SubjectResponse)
def detail(
    subject_id: SubjectId, user: CurrentUser, service: Service
) -> SubjectResponse:
    return service.detail(user.id, subject_id)


@router.put("/{subject_id}", response_model=SubjectResponse)
def update(
    subject_id: SubjectId, data: SubjectWrite, user: CurrentUser, service: Service
) -> SubjectResponse:
    return service.update(user.id, subject_id, data)


@router.post("/{subject_id}/archive", response_model=SubjectResponse)
def archive(
    subject_id: SubjectId, user: CurrentUser, service: Service
) -> SubjectResponse:
    return service.set_archived(user.id, subject_id, archived=True)


@router.post("/{subject_id}/reactivate", response_model=SubjectResponse)
def reactivate(
    subject_id: SubjectId, user: CurrentUser, service: Service
) -> SubjectResponse:
    return service.set_archived(user.id, subject_id, archived=False)


@router.delete("/{subject_id}", status_code=204)
def delete(
    subject_id: SubjectId,
    user: CurrentUser,
    service: Service,
    confirm: Annotated[
        Literal["true"], Query(description="Explicit irreversible deletion")
    ],
) -> Response:
    service.delete(user.id, subject_id)
    return Response(status_code=204)
