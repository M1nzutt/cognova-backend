from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth_dependencies import get_current_user
from app.database.dependencies import get_session
from app.models.user import User
from app.questionnaire.catalog import catalog_response
from app.schemas.error_response import ErrorResponse
from app.schemas.questionnaire_catalog_response import QuestionnaireCatalogResponse
from app.schemas.questionnaire_history_response import QuestionnaireHistoryResponse
from app.schemas.questionnaire_request import QuestionnaireRequest
from app.schemas.questionnaire_response import QuestionnaireResponse
from app.schemas.questionnaire_update_request import QuestionnaireUpdateRequest
from app.services.questionnaire_service import QuestionnaireService

router = APIRouter(
    prefix="/questionnaire",
    tags=["questionnaire"],
    responses={c: {"model": ErrorResponse} for c in (401, 404, 409, 422, 503)},
)
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_service(db: Annotated[Session, Depends(get_session)]) -> QuestionnaireService:
    return QuestionnaireService(db)


Service = Annotated[QuestionnaireService, Depends(get_service)]


@router.get("/catalog", response_model=QuestionnaireCatalogResponse)
def catalog(user: CurrentUser) -> QuestionnaireCatalogResponse:
    return catalog_response()


@router.get("/history", response_model=QuestionnaireHistoryResponse)
def history(
    user: CurrentUser,
    service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    before_revision: Annotated[int | None, Query(gt=0, le=2147483647)] = None,
) -> QuestionnaireHistoryResponse:
    return service.history(user.id, limit, before_revision)


@router.get("", response_model=QuestionnaireResponse)
def current(user: CurrentUser, service: Service) -> QuestionnaireResponse:
    return service.current(user.id)


@router.post("", status_code=201, response_model=QuestionnaireResponse)
def create(
    data: QuestionnaireRequest, user: CurrentUser, service: Service
) -> QuestionnaireResponse:
    return service.create(user.id, data)


@router.put("", response_model=QuestionnaireResponse)
def update(
    data: QuestionnaireUpdateRequest, user: CurrentUser, service: Service
) -> QuestionnaireResponse:
    return service.update(user.id, data)
