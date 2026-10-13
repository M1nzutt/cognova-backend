from datetime import datetime

from pydantic import BaseModel


class LegacyAcademicGoalResponse(BaseModel):
    value: str | None
    captured_at: datetime
