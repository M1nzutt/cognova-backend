from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class StudyPlanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    objective: str
    start_at: datetime
    end_at: datetime
    status: Literal["draft", "active", "completed", "abandoned"]
    source: Literal["ai", "manual"]
    created_at: datetime
    updated_at: datetime


__all__ = ["StudyPlanSummary"]
