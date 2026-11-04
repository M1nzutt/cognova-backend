from datetime import datetime

from pydantic import BaseModel


class StudySlotCandidateResponse(BaseModel):
    start_at: datetime
    end_at: datetime
    duration_minutes: int


__all__ = ["StudySlotCandidateResponse"]
