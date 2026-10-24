from pydantic import BaseModel, ConfigDict

from app.activities.types import ActivityStatus


class ActivityStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ActivityStatus
    expected_status: ActivityStatus
