from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class StudyPlanDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: Literal["accepted", "edited", "rejected", "regenerated"]
    field_path: str | None
    proposed_value: Any
    chosen_value: Any
    created_at: datetime


__all__ = ["StudyPlanDecisionResponse"]
