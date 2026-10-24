from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.activities.types import ActivityPriority, ActivityStatus, Deadline


class ActivityFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_id: Annotated[int | None, Field(gt=0, le=2147483647)] = None
    status: ActivityStatus | None = None
    priority: ActivityPriority | None = None
    deadline: Deadline | None = None
    deadline_from: Deadline | None = None
    deadline_to: Deadline | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 20
    after_id: Annotated[int | None, Field(gt=0, le=2147483647)] = None

    @model_validator(mode="after")
    def ordered_range(self) -> "ActivityFilters":
        if (
            self.deadline_from
            and self.deadline_to
            and self.deadline_from > self.deadline_to
        ):
            raise ValueError("Deadline range is reversed")
        return self
