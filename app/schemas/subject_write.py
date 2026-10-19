import unicodedata
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from app.subjects.catalog import ColorBase, ColorShade, SubjectDifficulty


def normalize_name(value: object) -> object:
    return (
        unicodedata.normalize("NFC", value).strip() if isinstance(value, str) else value
    )


class SubjectWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str, BeforeValidator(normalize_name), Field(min_length=1, max_length=20)
    ]
    difficulty: SubjectDifficulty
    color_base: ColorBase
    color_shade: ColorShade

    @field_validator("name")
    @classmethod
    def no_controls(cls, value: str) -> str:
        if any(unicodedata.category(char).startswith("C") for char in value):
            raise ValueError("Control characters are not allowed")
        return value

    @field_validator("color_shade", mode="before")
    @classmethod
    def strict_shade(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Shade must be an integer")
        return value
