from typing import Literal

from pydantic import BaseModel

from app.schemas.questionnaire_option import QuestionnaireOption


class QuestionnaireQuestion(BaseModel):
    id: str
    text: str
    selection: Literal["single", "multi"]
    min_choices: int
    max_choices: int
    options: list[QuestionnaireOption]
