import os
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.academic_intelligence.gemini_provider import GeminiProvider
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
    request: Request,
) -> BehaviorAnalysisResponse:
    request.app.state.rate_limiter.check("gemini-behavior", str(user.id))
    provider = GeminiProvider(
        os.environ.get("GEMINI_API_KEY"),
        request_id=getattr(request.state, "request_id", None),
    )
    return BehaviorAnalysisService(db, provider).analyze(user.id)
