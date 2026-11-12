from pydantic import BaseModel

from app.schemas.analytics_search_item import AnalyticsSearchItem


class AnalyticsSearchResponse(BaseModel):
    items: list[AnalyticsSearchItem]
    next_cursor: str | None


__all__ = ["AnalyticsSearchResponse"]
