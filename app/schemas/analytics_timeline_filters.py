from typing import Annotated, Literal

from pydantic import Field, field_validator

from app.schemas.analytics_range_filters import AnalyticsRangeFilters

AnalyticsCategory = Literal[
    "activity", "study_session", "decision", "plan", "challenge"
]


class AnalyticsTimelineFilters(AnalyticsRangeFilters):
    category: AnalyticsCategory | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 50
    cursor: Annotated[str | None, Field(max_length=2048)] = None

    @field_validator("limit", mode="before")
    @classmethod
    def reject_boolean_limit(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("Limit must be an integer")
        return value


__all__ = ["AnalyticsCategory", "AnalyticsTimelineFilters"]
