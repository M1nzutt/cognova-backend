from typing import Literal

from pydantic import BaseModel

from app.schemas.user_response import UserResponse


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: Literal["bearer"] = "bearer"
