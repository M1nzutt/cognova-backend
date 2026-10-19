from pydantic import BaseModel

from app.schemas.subject_response import SubjectResponse


class SubjectListResponse(BaseModel):
    items: list[SubjectResponse]
    next_after_id: int | None
