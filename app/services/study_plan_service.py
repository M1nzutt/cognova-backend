import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import TypeVar

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.domain_error import DomainError
from app.models.study_plans import (
    StudyChallenge,
    StudyPlan,
    StudyPlanActivity,
    StudyPlanDecision,
    StudyPlanSession,
    StudyPlanSubject,
)
from app.models.user import User
from app.schemas.study_plan_detail import StudyPlanDetail
from app.schemas.study_plan_list_response import StudyPlanListResponse
from app.schemas.study_plan_summary import StudyPlanSummary
from app.schemas.study_plan_write import StudyPlanWrite
from app.services.study_plan_projection import StudyPlanProjection
from app.services.study_plan_resources import StudyPlanResources
from app.study_plans.decision_entry import DecisionEntry
from app.study_plans.decision_history import DecisionHistory
from app.study_plans.proposal_provider import StudyPlanProposalProvider

T = TypeVar("T")


class StudyPlanService:
    """Owns Plan lifecycle, resource relations and append-only decisions."""

    _EDITABLE_FIELDS = ("name", "objective", "start_at", "end_at")

    def __init__(
        self,
        db: Session,
        clock: Callable[[], datetime] | None = None,
        proposal_provider: StudyPlanProposalProvider | None = None,
    ) -> None:
        self._db = db
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._proposal_provider = proposal_provider
        self._projection = StudyPlanProjection(db)
        self._resources = StudyPlanResources(db)

    def list(
        self,
        user_id: int,
        status: str,
        limit: int,
        after_id: int | None,
    ) -> StudyPlanListResponse:
        query = select(StudyPlan).where(StudyPlan.user_id == user_id)
        if status != "all":
            query = query.where(StudyPlan.status == status)
        if after_id is not None:
            query = query.where(StudyPlan.id > after_id)
        rows = self._db.scalars(query.order_by(StudyPlan.id).limit(limit + 1)).all()
        page = rows[:limit]
        return StudyPlanListResponse(
            items=[StudyPlanSummary.model_validate(plan) for plan in page],
            next_after_id=page[-1].id if len(rows) > limit and page else None,
        )

    def detail(self, user_id: int, plan_id: int) -> StudyPlanDetail:
        return self._projection.detail(self._owned(user_id, plan_id))

    def create(self, user_id: int, data: StudyPlanWrite) -> StudyPlanDetail:
        def insert() -> StudyPlanDetail:
            activities, sessions = self._resources.validate(user_id, data)
            self._resources.validate_schedule(data.start_at, data.end_at, sessions)
            plan = StudyPlan(
                user_id=user_id,
                name=data.name,
                objective=data.objective,
                start_at=data.start_at,
                end_at=data.end_at,
                status="draft",
                source="manual",
            )
            self._db.add(plan)
            self._db.flush()
            self._resources.replace(user_id, plan.id, data, activities, sessions)
            return self._projection.detail(plan)

        return self._write(user_id, insert)

    def update(
        self, user_id: int, plan_id: int, data: StudyPlanWrite
    ) -> StudyPlanDetail:
        def replace() -> StudyPlanDetail:
            plan = self._owned(user_id, plan_id, lock=True)
            self._require_draft(plan)
            activities, sessions = self._resources.validate(user_id, data)
            self._resources.validate_schedule(data.start_at, data.end_at, sessions)
            before = self._snapshot(plan)
            for field in self._EDITABLE_FIELDS:
                setattr(plan, field, getattr(data, field))
            self._resources.replace(user_id, plan.id, data, activities, sessions)
            after = self._snapshot(plan)
            if before == after:
                return self._projection.detail(plan)
            self._record_changes(user_id, plan.id, before, after)
            plan.updated_at = self._clock()
            self._db.flush()
            return self._projection.detail(plan)

        return self._write(user_id, replace)

    def delete(self, user_id: int, plan_id: int) -> None:
        def remove() -> None:
            plan = self._owned(user_id, plan_id, lock=True)
            if plan.source != "manual" or plan.status != "draft":
                raise DomainError("STUDY_PLAN_HISTORY_CONFLICT")
            if self._has_related_records(plan):
                raise DomainError("STUDY_PLAN_HISTORY_CONFLICT")
            self._db.delete(plan)
            self._db.flush()

        self._write(user_id, remove)

    def accept(self, user_id: int, plan_id: int) -> StudyPlanDetail:
        def accept_proposal() -> StudyPlanDetail:
            plan = self._owned(user_id, plan_id, lock=True)
            if plan.source != "ai" or plan.status != "draft":
                raise DomainError("STUDY_PLAN_STATE_CONFLICT")
            proposed = self._snapshot(plan)
            self._db.add(
                StudyPlanDecision(
                    user_id=user_id,
                    plan_id=plan.id,
                    action="accepted",
                    proposed_value=proposed,
                    chosen_value=proposed,
                )
            )
            plan.status = "active"
            plan.updated_at = self._clock()
            self._db.flush()
            return self._projection.detail(plan)

        return self._write(user_id, accept_proposal)

    def reject(self, user_id: int, plan_id: int) -> StudyPlanDetail:
        def reject_proposal() -> StudyPlanDetail:
            plan = self._owned(user_id, plan_id, lock=True)
            if plan.source != "ai" or plan.status != "draft":
                raise DomainError("STUDY_PLAN_STATE_CONFLICT")
            self._db.add(
                StudyPlanDecision(
                    user_id=user_id,
                    plan_id=plan.id,
                    action="rejected",
                    proposed_value=self._snapshot(plan),
                    chosen_value=None,
                )
            )
            plan.status = "abandoned"
            plan.updated_at = self._clock()
            self._db.flush()
            return self._projection.detail(plan)

        return self._write(user_id, reject_proposal)

    def regenerate(self, user_id: int, plan_id: int) -> StudyPlanDetail:
        def regenerate_proposal() -> StudyPlanDetail:
            plan = self._owned(user_id, plan_id, lock=True)
            if plan.source != "ai" or plan.status != "draft":
                raise DomainError("STUDY_PLAN_STATE_CONFLICT")
            if self._proposal_provider is None:
                raise DomainError("STUDY_PLAN_GENERATION_UNAVAILABLE")
            proposed = self._proposal_provider.regenerate(plan)
            activities, sessions = self._resources.validate(user_id, proposed)
            self._resources.validate_schedule(
                proposed.start_at, proposed.end_at, sessions
            )
            self._db.add(
                StudyPlanDecision(
                    user_id=user_id,
                    plan_id=plan.id,
                    action="regenerated",
                    proposed_value=self._snapshot(plan),
                    chosen_value=None,
                )
            )
            self._apply_write(plan, proposed)
            self._resources.replace(user_id, plan.id, proposed, activities, sessions)
            plan.updated_at = self._clock()
            self._db.flush()
            return self._projection.detail(plan)

        return self._write(user_id, regenerate_proposal)

    def activate(self, user_id: int, plan_id: int) -> StudyPlanDetail:
        return self._transition(
            user_id, plan_id, allowed={"draft"}, target="active", manual_only=True
        )

    def complete(self, user_id: int, plan_id: int) -> StudyPlanDetail:
        return self._transition(
            user_id, plan_id, allowed={"active"}, target="completed"
        )

    def abandon(self, user_id: int, plan_id: int) -> StudyPlanDetail:
        return self._transition(
            user_id, plan_id, allowed={"draft", "active"}, target="abandoned"
        )

    def undo(self, user_id: int, plan_id: int) -> StudyPlanDetail:
        def reverse_latest() -> StudyPlanDetail:
            plan = self._owned(user_id, plan_id, lock=True)
            self._require_draft(plan)
            rows = self._db.scalars(
                select(StudyPlanDecision)
                .where(
                    StudyPlanDecision.user_id == user_id,
                    StudyPlanDecision.plan_id == plan.id,
                )
                .order_by(StudyPlanDecision.created_at, StudyPlanDecision.id)
            ).all()
            history = DecisionHistory(
                [
                    DecisionEntry(
                        row.id,
                        row.action,
                        row.field_path,
                        row.proposed_value,
                        row.chosen_value,
                        row.created_at,
                    )
                    for row in rows
                ]
            )
            latest = history.undo_latest()
            if latest is None or latest.action != "edited" or not latest.field_path:
                raise DomainError("STUDY_PLAN_HISTORY_CONFLICT")
            before = self._snapshot(plan)
            self._apply_decision_value(plan, latest.field_path, latest.proposed_value)
            after = self._snapshot(plan)
            if before == after:
                raise DomainError("STUDY_PLAN_HISTORY_CONFLICT")
            self._record_undo(user_id, plan.id, latest)
            plan.updated_at = self._clock()
            self._db.flush()
            return self._projection.detail(plan)

        return self._write(user_id, reverse_latest)

    def _transition(
        self,
        user_id: int,
        plan_id: int,
        *,
        allowed: set[str],
        target: str,
        manual_only: bool = False,
    ) -> StudyPlanDetail:
        def change() -> StudyPlanDetail:
            plan = self._owned(user_id, plan_id, lock=True)
            if plan.status not in allowed or (manual_only and plan.source != "manual"):
                raise DomainError("STUDY_PLAN_STATE_CONFLICT")
            plan.status = target
            plan.updated_at = self._clock()
            self._db.flush()
            return self._projection.detail(plan)

        return self._write(user_id, change)

    def _owned(self, user_id: int, plan_id: int, *, lock: bool = False) -> StudyPlan:
        query = select(StudyPlan).where(
            StudyPlan.id == plan_id, StudyPlan.user_id == user_id
        )
        if lock:
            query = query.with_for_update()
        plan = self._db.scalar(query.execution_options(populate_existing=True))
        if plan is None:
            raise DomainError("STUDY_PLAN_NOT_FOUND")
        return plan

    def _snapshot(self, plan: StudyPlan) -> dict[str, object]:
        return self._resources.snapshot(plan)

    def _record_changes(
        self,
        user_id: int,
        plan_id: int,
        before: dict[str, object],
        after: dict[str, object],
    ) -> None:
        for field_path, old_value in before.items():
            chosen_value = after[field_path]
            if old_value == chosen_value:
                continue
            self._db.add(
                StudyPlanDecision(
                    user_id=user_id,
                    plan_id=plan_id,
                    action="edited",
                    field_path=field_path,
                    proposed_value=old_value,
                    chosen_value=chosen_value,
                )
            )

    def _record_undo(self, user_id: int, plan_id: int, decision: DecisionEntry) -> None:
        if decision.field_path is None:
            raise DomainError("STUDY_PLAN_HISTORY_CONFLICT")
        self._db.add(
            StudyPlanDecision(
                user_id=user_id,
                plan_id=plan_id,
                action="edited",
                field_path=f"undo:{decision.id}:{decision.field_path}",
                proposed_value=decision.chosen_value,
                chosen_value=decision.proposed_value,
            )
        )

    def _apply_write(self, plan: StudyPlan, data: StudyPlanWrite) -> None:
        for field in self._EDITABLE_FIELDS:
            setattr(plan, field, getattr(data, field))

    def _apply_decision_value(
        self, plan: StudyPlan, field_path: str, value: object
    ) -> None:
        if field_path in self._EDITABLE_FIELDS:
            if field_path in {"start_at", "end_at"}:
                if not isinstance(value, str):
                    raise DomainError("STUDY_PLAN_HISTORY_CONFLICT")
                try:
                    value = datetime.fromisoformat(value)
                except ValueError:
                    raise DomainError("STUDY_PLAN_HISTORY_CONFLICT") from None
            if field_path == "name":
                if not isinstance(value, str):
                    raise DomainError("STUDY_PLAN_HISTORY_CONFLICT")
                plan.name = value
            elif field_path == "objective":
                if not isinstance(value, str):
                    raise DomainError("STUDY_PLAN_HISTORY_CONFLICT")
                plan.objective = value
            elif field_path == "start_at":
                if not isinstance(value, datetime):
                    raise DomainError("STUDY_PLAN_HISTORY_CONFLICT")
                plan.start_at = value
            else:
                if not isinstance(value, datetime):
                    raise DomainError("STUDY_PLAN_HISTORY_CONFLICT")
                plan.end_at = value
            self._validate_current_resources(plan)
            return
        self._resources.restore_field(plan, field_path, value)

    def _validate_current_resources(self, plan: StudyPlan) -> None:
        self._resources.validate_current(plan)

    def _has_related_records(self, plan: StudyPlan) -> bool:
        checks = (
            select(StudyPlanSubject.user_id).where(
                StudyPlanSubject.user_id == plan.user_id,
                StudyPlanSubject.plan_id == plan.id,
            ),
            select(StudyPlanActivity.user_id).where(
                StudyPlanActivity.user_id == plan.user_id,
                StudyPlanActivity.plan_id == plan.id,
            ),
            select(StudyPlanSession.user_id).where(
                StudyPlanSession.user_id == plan.user_id,
                StudyPlanSession.plan_id == plan.id,
            ),
            select(StudyPlanDecision.id).where(
                StudyPlanDecision.user_id == plan.user_id,
                StudyPlanDecision.plan_id == plan.id,
            ),
            select(StudyChallenge.id).where(
                StudyChallenge.user_id == plan.user_id,
                StudyChallenge.plan_id == plan.id,
            ),
        )
        return any(self._db.scalar(query.limit(1)) is not None for query in checks)

    def _require_draft(self, plan: StudyPlan) -> None:
        if plan.status != "draft":
            raise DomainError("STUDY_PLAN_STATE_CONFLICT")

    def _write(self, user_id: int, operation: Callable[[], T]) -> T:
        self._db.rollback()
        for attempt in range(3):
            try:
                self._db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                owner = self._db.scalar(
                    select(User.id).where(User.id == user_id).with_for_update()
                )
                if owner is None:
                    raise DomainError("STUDY_PLAN_NOT_FOUND")
                result = operation()
                self._db.commit()
                return result
            except DomainError:
                self._db.rollback()
                raise
            except DBAPIError as exc:
                self._db.rollback()
                state = getattr(exc.orig, "sqlstate", None)
                if state in {"40001", "40P01"} and attempt < 2:
                    time.sleep(0.01 * (attempt + 1))
                    continue
                if state in {"40001", "40P01"}:
                    raise DomainError("STUDY_PLAN_WRITE_CONFLICT") from None
                constraint = getattr(
                    getattr(exc.orig, "diag", None), "constraint_name", None
                )
                if constraint in {
                    "fk_study_challenges_plan_subject",
                    "fk_study_challenges_plan_activity",
                    "fk_study_challenges_plan_session",
                }:
                    raise DomainError("STUDY_PLAN_HISTORY_CONFLICT") from None
                if state == "23503" or state == "23505":
                    raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT") from None
                if state == "23514":
                    raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT") from None
                if constraint:
                    raise DomainError("STUDY_PLAN_RESOURCE_CONFLICT") from None
                raise
            except Exception:
                self._db.rollback()
                raise
        raise AssertionError("unreachable")


__all__ = ["StudyPlanService"]
