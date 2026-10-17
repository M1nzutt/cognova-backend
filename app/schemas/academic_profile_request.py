from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class AcademicProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    degree_program: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ]
    semester: int = Field(gt=0, le=2147483647, strict=True)
