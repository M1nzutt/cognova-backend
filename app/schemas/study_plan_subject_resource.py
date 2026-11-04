from pydantic import BaseModel


class StudyPlanSubjectResource(BaseModel):
    id: int
    name: str


__all__ = ["StudyPlanSubjectResource"]
