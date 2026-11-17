from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AcademicChatMessageWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or any(
            ord(character) < 32 and character not in "\t\n\r" for character in cleaned
        ):
            raise ValueError("Message cannot be blank")
        return cleaned


class AcademicConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class AcademicMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: Literal["user", "assistant"]
    content: str
    evidence: list[str]
    created_at: datetime


class AcademicConversationListResponse(BaseModel):
    items: list[AcademicConversationResponse]


class AcademicMessagePageResponse(BaseModel):
    items: list[AcademicMessageResponse]
    next_before_id: int | None


class AcademicChatSendResponse(BaseModel):
    conversation: AcademicConversationResponse
    user_message: AcademicMessageResponse
    assistant_message: AcademicMessageResponse
