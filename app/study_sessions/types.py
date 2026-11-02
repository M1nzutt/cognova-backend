from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

EntityId = Annotated[int, Field(strict=True, gt=0, le=2147483647)]
SessionExecutionState = Literal["planned", "running", "paused", "finished"]
SessionResult = Literal["completed", "partial", "postponed", "cancelled"]
SessionContext = Literal[
    "finished_early", "distracted", "tired", "interrupted", "changed_activity", "other"
]
Instant = AwareDatetime

__all__ = [
    "EntityId",
    "Instant",
    "SessionContext",
    "SessionExecutionState",
    "SessionResult",
    "datetime",
]
