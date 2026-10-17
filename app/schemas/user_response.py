from pydantic import BaseModel, ConfigDict, EmailStr

from app.schemas.legacy_academic_goal_response import LegacyAcademicGoalResponse
from app.schemas.onboarding_response import OnboardingResponse


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    degree_program: str | None
    semester: int | None
    onboarding: OnboardingResponse
    legacy_academic_goal: LegacyAcademicGoalResponse | None
