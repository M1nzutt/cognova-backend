from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AccessClaims(BaseModel):
    sub: str = Field(pattern=r"^[1-9][0-9]{0,9}$")
    sid: UUID
    type: Literal["access"]
    iat: int = Field(strict=True, ge=0)
    exp: int = Field(strict=True, gt=0)

    @field_validator("sub")
    @classmethod
    def validate_subject(cls, subject: str) -> str:
        if int(subject) > 2147483647:
            raise ValueError("User ID out of range")
        return subject
