from collections import Counter
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.academic_intelligence.academic_context import AcademicContext
from app.models.study_session import StudySession
from app.schemas.behavior_analysis_response import (
    BehaviorAnalysisResponse,
    BehaviorEvidence,
    BehaviorObservation,
    RelatedResource,
)


class BehaviorAnalysisService:
    _MAX_EVIDENCE = 10

    def __init__(self, db: Session) -> None:
        self._db = db

    def analyze(self, user_id: int) -> BehaviorAnalysisResponse:
        context = AcademicContext(self._db, user_id)
        completed_count = (
            self._db.scalar(
                select(func.count())
                .select_from(StudySession)
                .where(
                    StudySession.user_id == user_id,
                    StudySession.execution_state == "finished",
                    StudySession.status == "completed",
                    StudySession.actual_duration > 0,
                )
            )
            or 0
        )
        reviewed_count = (
            self._db.scalar(
                select(func.count())
                .select_from(StudySession)
                .where(
                    StudySession.user_id == user_id,
                    StudySession.execution_state == "finished",
                    StudySession.status.in_(("completed", "partial")),
                    StudySession.actual_duration > 0,
                )
            )
            or 0
        )
        observed_rows = [
            row
            for row in context.sessions
            if row.execution_state == "finished"
            and row.status in ("completed", "partial")
            and row.actual_duration > 0
        ]
        evidence_rows = observed_rows[: self._MAX_EVIDENCE]
        evidence = [self._evidence_item(row, context) for row in evidence_rows]
        observations = []
        if evidence:
            differences = sum(
                abs(
                    Decimal(item.actual_seconds)
                    - Decimal(item.planned_minutes) * Decimal(60)
                )
                >= Decimal(1)
                for item in evidence
            )
            common_planned, common_actual = Counter(
                (
                    item.planned_minutes,
                    self._rounded_minutes(Decimal(item.actual_seconds)),
                )
                for item in evidence
            ).most_common(1)[0][0]
            common_count = sum(
                item.planned_minutes == common_planned
                and self._rounded_minutes(Decimal(item.actual_seconds))
                == common_actual
                for item in evidence
            )
            if differences and (common_count > 1 or len(evidence) == 1):
                observation = (
                    f"En {common_count} de {len(evidence)} registros se "
                    f"registró cerca de {self._duration_label(common_actual)} "
                    f"frente a {self._duration_label(common_planned)} "
                    "planificados."
                )
            elif differences:
                observation = (
                    f"El tiempo real difiere del planificado en {differences} "
                    f"de {len(evidence)} registros mostrados."
                )
            else:
                observation = (
                    f"El tiempo real coincide con el planificado en los "
                    f"{len(evidence)} registros mostrados."
                )
            if reviewed_count > len(evidence):
                observation += (
                    f" Se muestran los más recientes de {reviewed_count} registros."
                )
            observations.append(
                BehaviorObservation(
                    observation=observation,
                    interpretation=(
                        "Estos datos describen solo las sesiones registradas; "
                        "no explican la diferencia ni permiten concluir que sea "
                        "un hábito."
                    ),
                    evidence=evidence,
                    question=(
                        "¿Qué contexto ayudaría a entender la diferencia entre "
                        "el tiempo previsto y el registrado?"
                    ),
                    confidence_basis=(
                        f"Se basa en {len(evidence)} "
                        f"{'registro' if len(evidence) == 1 else 'registros'} "
                        "finalizados o parciales; las sesiones parciales "
                        "se identifican por "
                        "separado y no cuentan como completadas."
                    ),
                    related_resources=self._related_resources(evidence_rows, context),
                )
            )
        return BehaviorAnalysisResponse(
            completed_session_count=completed_count,
            reviewed_session_count=reviewed_count,
            state="factual_summary" if observations else "insufficient_data",
            observations=observations,
        )

    @staticmethod
    def _evidence_item(row: StudySession, context: AcademicContext) -> BehaviorEvidence:
        subject = next(
            (item for item in context.subjects if item.id == row.subject_id), None
        )
        activity = next(
            (item for item in context.activities if item.id == row.activity_id), None
        )
        context_label = subject.name if subject else "Sesión"
        if activity:
            context_label += f" · {activity.title}"
        actual = Decimal(row.actual_duration)
        return BehaviorEvidence(
            session_id=row.id,
            planned_minutes=row.planned_duration,
            actual_seconds=format(actual, "f"),
            result=row.status,
            summary=f"{context_label}: {row.planned_duration} min planificados",
        )

    @staticmethod
    def _rounded_minutes(seconds: Decimal) -> int:
        return int((seconds + Decimal(30)) // Decimal(60))

    @staticmethod
    def _duration_label(minutes: int) -> str:
        hours, remainder = divmod(minutes, 60)
        if hours and remainder:
            return f"{hours} h {remainder} min"
        if hours:
            return f"{hours} h"
        return f"{minutes} min"

    @staticmethod
    def _related_resources(
        rows: list[StudySession], context: AcademicContext
    ) -> list[RelatedResource]:
        resources: dict[tuple[str, int], RelatedResource] = {}
        subjects = {item.id: item for item in context.subjects}
        activities = {item.id: item for item in context.activities}
        for row in rows:
            subject = subjects.get(row.subject_id)
            if subject:
                resources[("subject", subject.id)] = RelatedResource(
                    kind="subject",
                    id=subject.id,
                    label=subject.name,
                    href=f"/app/subjects/{subject.id}",
                )
            activity = (
                activities.get(row.activity_id) if row.activity_id is not None else None
            )
            if activity:
                resources[("activity", activity.id)] = RelatedResource(
                    kind="activity",
                    id=activity.id,
                    label=activity.title,
                    href=f"/app/activities/{activity.id}",
                )
            session_label = subject.name if subject else "Sesión"
            if activity:
                session_label += f" · {activity.title}"
            resources[("session", row.id)] = RelatedResource(
                kind="session",
                id=row.id,
                label=f"{session_label} · {row.planned_start_at:%d/%m %H:%M}",
                href=f"/app/sessions/{row.id}",
            )
        return list(resources.values())
