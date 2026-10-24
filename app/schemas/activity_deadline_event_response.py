from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ActivityDeadlineEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    revision: int
    previous_deadline: datetime
    new_deadline: datetime
    event_type: Literal["postponed", "rescheduled"]
    occurred_at: datetime
