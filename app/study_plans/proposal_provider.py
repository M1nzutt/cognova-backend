from typing import Protocol

from app.models.study_plans import StudyPlan
from app.schemas.study_plan_write import StudyPlanWrite


class StudyPlanProposalProvider(Protocol):
    """Future adapter boundary for a real proposal provider such as Gemini."""

    def regenerate(self, plan: StudyPlan) -> StudyPlanWrite: ...


__all__ = ["StudyPlanProposalProvider"]
