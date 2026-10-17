from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.auth_dependencies import get_current_user
from app.api.onboarding_dependencies import get_onboarding_service
from app.models.user import User
from app.schemas.academic_profile_request import AcademicProfileRequest
from app.schemas.error_response import ErrorResponse
from app.schemas.user_response import UserResponse
from app.services.onboarding_service import OnboardingService

router = APIRouter(
    prefix="/onboarding",
    tags=["onboarding"],
    responses={c: {"model": ErrorResponse} for c in (401, 409, 422, 503)},
)


@router.put("/academic-profile", response_model=UserResponse)
def save_academic_profile(
    data: AcademicProfileRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OnboardingService, Depends(get_onboarding_service)],
) -> UserResponse:
    return service.save_academic_profile(user.id, data)
