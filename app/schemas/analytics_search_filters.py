from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalyticsSearchFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prefix: Annotated[str, Field(min_length=1, max_length=64)]
    type: Literal["subject", "activity", "study_plan", "study_challenge"] | None = None
    limit: Annotated[int, Field(ge=1, le=50)] = 20
    cursor: Annotated[str | None, Field(max_length=2048)] = None

    @field_validator("prefix")
    @classmethod
    def trim_prefix(cls, value: str) -> str:
        value = value.strip()
        if not value or len(value) > 64:
            raise ValueError("Prefix must contain 1 to 64 non-space characters")
        return value

    @field_validator("limit", mode="before")
    @classmethod
    def reject_boolean_limit(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("Limit must be an integer")
        return value


__all__ = ["AnalyticsSearchFilters"]
