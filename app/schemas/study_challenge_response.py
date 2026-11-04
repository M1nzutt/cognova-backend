from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.study_challenge_write import ChallengeTarget


class StudyChallengeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    subject_id: int | None
    activity_id: int | None
    study_session_id: int | None
    title: str
    description: str
    target_type: ChallengeTarget
    target_value: dict[str, Any]
    start_at: datetime | None
    deadline: datetime | None
    status: Literal["pending", "in_progress", "completed", "failed", "cancelled"]
    source: Literal["ai", "manual"]
    generation_criteria: dict[str, Any]
    created_at: datetime
    updated_at: datetime


__all__ = ["StudyChallengeResponse"]
