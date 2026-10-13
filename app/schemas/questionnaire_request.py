from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.questionnaire_answers import QuestionnaireAnswers


class QuestionnaireRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    questionnaire_version: Literal[1]
    answers: QuestionnaireAnswers

    @field_validator("questionnaire_version", mode="before")
    @classmethod
    def strict_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Questionnaire version must be an integer")
        return value
