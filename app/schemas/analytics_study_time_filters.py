from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator

from app.schemas.analytics_range_filters import AnalyticsRangeFilters


class AnalyticsStudyTimeFilters(AnalyticsRangeFilters):
    granularity: Literal["day", "week", "month"] = "day"
    timezone: Annotated[str, Field(min_length=1, max_length=100)] = "UTC"

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("Use an IANA timezone") from exc
        return value


__all__ = ["AnalyticsStudyTimeFilters"]
