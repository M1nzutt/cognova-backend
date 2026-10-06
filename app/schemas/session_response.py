from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: UUID
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    current: bool
