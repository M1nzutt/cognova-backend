from pydantic import BaseModel


class QuestionnaireOption(BaseModel):
    id: str
    label: str
