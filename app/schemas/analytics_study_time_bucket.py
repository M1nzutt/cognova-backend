from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsStudyTimeBucket(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_at: datetime = Field(alias="from")
    to_at: datetime = Field(alias="to")
    seconds: str
    minutes: str


__all__ = ["AnalyticsStudyTimeBucket"]
