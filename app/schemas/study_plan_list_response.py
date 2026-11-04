from pydantic import BaseModel

from app.schemas.study_plan_summary import StudyPlanSummary


class StudyPlanListResponse(BaseModel):
    items: list[StudyPlanSummary]
    next_after_id: int | None


__all__ = ["StudyPlanListResponse"]
