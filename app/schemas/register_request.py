from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    StringConstraints,
    field_validator,
)


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    email: EmailStr
    password: SecretStr = Field(min_length=8)
    degree_program: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ]
    semester: int = Field(gt=0, strict=True)
    academic_goal: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()
