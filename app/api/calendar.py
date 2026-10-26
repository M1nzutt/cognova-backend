from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.onboarding_dependencies import get_onboarded_user
from app.database.dependencies import get_session
from app.models.user import User
from app.schemas.calendar_filters import CalendarFilters
from app.schemas.calendar_response import CalendarResponse
from app.schemas.error_response import ErrorResponse
from app.services.calendar_service import CalendarService

router = APIRouter(
    prefix="/calendar",
    tags=["calendar"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 422, 503)},
)


def get_service(db: Annotated[Session, Depends(get_session)]) -> CalendarService:
    return CalendarService(db)


@router.get("", response_model=CalendarResponse)
def list_calendar(
    user: Annotated[User, Depends(get_onboarded_user)],
    service: Annotated[CalendarService, Depends(get_service)],
    filters: Annotated[CalendarFilters, Query()],
) -> CalendarResponse:
    return service.list(user.id, filters)
