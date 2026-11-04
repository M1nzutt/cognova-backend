from pydantic import BaseModel

from app.schemas.study_challenge_response import StudyChallengeResponse


class StudyChallengeListResponse(BaseModel):
    items: list[StudyChallengeResponse]
    next_after_id: int | None


__all__ = ["StudyChallengeListResponse"]
