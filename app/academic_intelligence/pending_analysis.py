from dataclasses import dataclass


@dataclass(slots=True)
class PendingAnalysis:
    """One evidence candidate awaiting deterministic or model review."""

    kind: str
    resource_id: int
    subject_id: int | None
    following: "PendingAnalysis | None" = None


__all__ = ["PendingAnalysis"]
