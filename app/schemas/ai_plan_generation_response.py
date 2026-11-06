from pydantic import BaseModel, Field

from app.schemas.study_plan_detail import StudyPlanDetail


class AiPlanGenerationResponse(BaseModel):
    plan: StudyPlanDetail
    explanation: str = Field(min_length=1, max_length=2000)
    reasoning_summary: str = Field(min_length=1, max_length=2000)
