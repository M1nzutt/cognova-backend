from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.questionnaire.catalog import BY_ID
from app.schemas.questionnaire_answer import QuestionnaireAnswer


class QuestionnaireAnswers(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    q1: QuestionnaireAnswer
    q2: QuestionnaireAnswer
    q3: QuestionnaireAnswer
    q4: QuestionnaireAnswer
    q5: QuestionnaireAnswer
    q6: QuestionnaireAnswer
    q7: QuestionnaireAnswer
    q8: QuestionnaireAnswer
    q9: QuestionnaireAnswer
    q10: QuestionnaireAnswer

    @model_validator(mode="after")
    def validate_catalog_choices(self) -> Self:
        for question_id, question in BY_ID.items():
            answer: QuestionnaireAnswer = getattr(self, question_id)
            choices = answer.choices
            if len(choices) > question.max_choices or len(choices) != len(set(choices)):
                raise ValueError(f"Invalid selection count for {question_id}")
            if set(choices) - {option.id for option in question.options}:
                raise ValueError(f"Unknown option for {question_id}")
            if ("other" in choices) != (answer.other_text is not None):
                raise ValueError(
                    f"Other text does not match selection for {question_id}"
                )
        return self
