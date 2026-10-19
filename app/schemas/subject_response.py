from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.subjects.catalog import SubjectDifficulty, SubjectStatus


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: SubjectStatus
    difficulty: SubjectDifficulty
    # DB permits a broader color vocabulary than the write API.
    color_base: str
    color_shade: int
    created_at: datetime
    updated_at: datetime
