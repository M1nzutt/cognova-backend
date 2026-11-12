from typing import Literal

from pydantic import BaseModel


class AnalyticsSearchItem(BaseModel):
    type: Literal["subject", "activity", "study_plan", "study_challenge"]
    id: int
    title: str
    subject_id: int | None
    plan_id: int | None
    status: str | None


__all__ = ["AnalyticsSearchItem"]
