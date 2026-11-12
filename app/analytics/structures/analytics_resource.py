"""Small immutable, user-scoped resource projection for Analytics indexes."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalyticsResource:
    resource_type: str
    resource_id: int
    title: str
    subject_id: int | None = None
    plan_id: int | None = None
    status: str | None = None

    @property
    def key(self) -> tuple[str, int]:
        return self.resource_type, self.resource_id


__all__ = ["AnalyticsResource"]
