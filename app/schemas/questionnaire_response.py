from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.questionnaire_answers import QuestionnaireAnswers


class QuestionnaireResponse(BaseModel):
    revision: int
    questionnaire_version: Literal[1] = 1
    answers: QuestionnaireAnswers
    recorded_at: datetime
