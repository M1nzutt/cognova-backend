from datetime import timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.activities.types import Deadline


class AnalyticsRangeFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_at: Deadline = Field(alias="from")
    to_at: Deadline = Field(alias="to")

    @model_validator(mode="after")
    def validate_range(self) -> "AnalyticsRangeFilters":
        start = self.from_at.astimezone(timezone.utc)
        end = self.to_at.astimezone(timezone.utc)
        if not timedelta(0) < end - start <= timedelta(days=366):
            raise ValueError("Use a positive range of at most 366 days")
        return self


__all__ = ["AnalyticsRangeFilters"]
