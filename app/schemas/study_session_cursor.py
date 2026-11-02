from datetime import datetime

from pydantic import BaseModel

from app.study_sessions.types import EntityId


class StudySessionCursor(BaseModel):
    after_planned_start_at: datetime
    after_id: EntityId
