from typing import Literal

from pydantic import BaseModel

from app.schemas.questionnaire_question import QuestionnaireQuestion


class QuestionnaireCatalogResponse(BaseModel):
    questionnaire_version: Literal[1] = 1
    questions: list[QuestionnaireQuestion]
