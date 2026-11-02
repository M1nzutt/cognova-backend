from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.study_sessions.types import SessionContext, SessionResult


class StudySessionFinish(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: SessionResult
    context: SessionContext | None = None
    other_text: Annotated[str | None, Field(max_length=200)] = None

    @field_validator("other_text")
    @classmethod
    def strip_other_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_other_text(self) -> "StudySessionFinish":
        if self.context == "other":
            if self.other_text is None or not self.other_text:
                raise ValueError("other_text is required for context=other")
        elif self.other_text is not None:
            raise ValueError("other_text only applies to context=other")
        return self
