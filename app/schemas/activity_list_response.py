from pydantic import BaseModel

from app.schemas.activity_response import ActivityResponse


class ActivityListResponse(BaseModel):
    items: list[ActivityResponse]
    next_after_id: int | None
