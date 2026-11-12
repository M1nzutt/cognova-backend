from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analytics_study_time_bucket import AnalyticsStudyTimeBucket
from app.schemas.analytics_study_time_subject import AnalyticsStudyTimeSubject


class AnalyticsStudyTimeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_at: datetime = Field(alias="from")
    to_at: datetime = Field(alias="to")
    timezone: str
    granularity: Literal["day", "week", "month"]
    total_seconds: str
    total_minutes: str
    sessions_count: int
    by_subject: list[AnalyticsStudyTimeSubject]
    buckets: list[AnalyticsStudyTimeBucket]


__all__ = ["AnalyticsStudyTimeResponse"]
