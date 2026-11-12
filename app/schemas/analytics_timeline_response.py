from pydantic import BaseModel

from app.schemas.analytics_timeline_item import AnalyticsTimelineItem


class AnalyticsTimelineResponse(BaseModel):
    items: list[AnalyticsTimelineItem]
    next_cursor: str | None


__all__ = ["AnalyticsTimelineResponse"]
