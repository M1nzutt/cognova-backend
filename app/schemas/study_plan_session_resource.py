from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.study_sessions.types import (
    SessionContext,
    SessionExecutionState,
    SessionResult,
)


class StudyPlanSessionResource(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_id: int
    activity_id: int | None
    planned_start_at: datetime
    planned_duration: int
    execution_state: SessionExecutionState
    status: SessionResult | None
    start_at: datetime | None
    end_at: datetime | None
    actual_duration: Decimal
    context: SessionContext | None


__all__ = ["StudyPlanSessionResource"]
