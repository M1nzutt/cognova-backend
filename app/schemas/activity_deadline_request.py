from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.activities.types import Deadline


class ActivityDeadlineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deadline: Deadline
    expected_revision: Annotated[int, Field(strict=True, ge=0, le=2147483647)]
