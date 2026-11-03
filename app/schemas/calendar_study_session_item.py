from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.study_sessions.types import SessionExecutionState, SessionResult


class CalendarStudySessionItem(BaseModel):
    """Read-only calendar projection of an original study session."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: Literal["study_session"] = "study_session"
    subject_id: int
    activity_id: int | None
    planned_start_at: datetime
    planned_duration: int
    lifecycle: SessionExecutionState
    result: SessionResult | None
    start_at: datetime | None
    end_at: datetime | None
