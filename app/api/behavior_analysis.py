from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.onboarding_dependencies import get_onboarded_user
from app.database.dependencies import get_session
from app.models.user import User
from app.schemas.behavior_analysis_response import BehaviorAnalysisResponse
from app.schemas.error_response import ErrorResponse
from app.services.behavior_analysis_service import BehaviorAnalysisService

router = APIRouter(
    prefix="/analysis",
    tags=["analysis"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 429, 503)},
)


@router.post("/behavior", response_model=BehaviorAnalysisResponse)
def analyze_behavior(
    user: Annotated[User, Depends(get_onboarded_user)],
    db: Annotated[Session, Depends(get_session)],
) -> BehaviorAnalysisResponse:
    return BehaviorAnalysisService(db).analyze(user.id)
