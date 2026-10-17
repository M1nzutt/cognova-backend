from typing import Literal

from pydantic import BaseModel

from app.schemas.onboarding_status import OnboardingStatus


class OnboardingResponse(BaseModel):
    status: OnboardingStatus
    academic_profile_complete: bool
    questionnaire_complete: bool
    next_step: Literal["academic_profile", "questionnaire", "complete"]
