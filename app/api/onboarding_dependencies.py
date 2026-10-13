from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.auth_dependencies import get_current_user
from app.database.dependencies import get_session
from app.models.user import User
from app.services.onboarding_service import OnboardingService


def get_onboarding_service(
    db: Annotated[Session, Depends(get_session)],
) -> OnboardingService:
    return OnboardingService(db)


def get_onboarded_user(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[OnboardingService, Depends(get_onboarding_service)],
) -> User:
    """Required by future academic routers; never by auth/onboarding itself."""
    return service.require_complete(user)
