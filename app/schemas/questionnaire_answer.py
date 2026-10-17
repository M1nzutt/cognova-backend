from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictStr, StringConstraints


class QuestionnaireAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    choices: list[StrictStr] = Field(min_length=1, max_length=3, strict=True)
    other_text: (
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
        ]
        | None
    ) = None
