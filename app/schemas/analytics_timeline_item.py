from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.analytics_timeline_filters import AnalyticsCategory


class AnalyticsTimelineItem(BaseModel):
    event_id: str
    occurred_at: datetime
    category: AnalyticsCategory
    event_type: str
    resource_type: str
    resource_id: int
    title: str
    subject_id: int | None
    subject_name: str | None
    details: dict[str, Any]


__all__ = ["AnalyticsTimelineItem"]
