from app.schemas.subject_write import SubjectWrite
from app.subjects.catalog import SubjectStatus


class SubjectCreate(SubjectWrite):
    status: SubjectStatus = "active"
