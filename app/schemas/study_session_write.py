from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.study_sessions.types import EntityId, Instant


class StudySessionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: EntityId
    activity_id: EntityId | None = None
    planned_start_at: Instant
    planned_duration: Annotated[int, Field(strict=True, ge=10, le=180)]
