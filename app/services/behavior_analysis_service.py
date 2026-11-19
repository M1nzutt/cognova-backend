import hashlib
import json
import re
import threading
import time
from collections import Counter
from collections.abc import Callable
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.academic_intelligence.academic_context import AcademicContext
from app.academic_intelligence.gemini_schemas import BehaviorInsight
from app.models.study_session import StudySession
from app.schemas.behavior_analysis_response import (
    BehaviorAnalysisResponse,
    BehaviorEvidence,
    BehaviorObservation,
    RelatedResource,
)


class BehaviorAnalysisService:
    _MAX_EVIDENCE = 10
    _CACHE_TTL_SECONDS = 1800
    _MAX_CACHE_ENTRIES = 256
    _CACHE: dict[
        str,
        tuple[
            float,
            BehaviorInsight,
            Literal["gemini", "deterministic", "fallback"],
        ],
    ] = {}
    _CACHE_LOCK = threading.Lock()
    _CACHE_CONDITION = threading.Condition(_CACHE_LOCK)
    _CACHE_INFLIGHT: set[str] = set()
    _UNSAFE_TERMS = re.compile(
        r"\b(disciplina|motivaci[oó]n|constancia|pereza|procrastinaci[oó]n|"
        r"diagn[oó]stic\w*|h[aá]bito\w*)\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        db: Session,
        insight_generator: Callable[[str], BehaviorInsight] | None = None,
    ) -> None:
        self._db = db
        self._insight_generator = insight_generator

    def analyze(
        self,
        user_id: int,
        on_gemini_request: Callable[[], None] | None = None,
    ) -> BehaviorAnalysisResponse:
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
        partial_count = (
            self._db.scalar(
                select(func.count())
                .select_from(StudySession)
                .where(
                    StudySession.user_id == user_id,
                    StudySession.execution_state == "finished",
                    StudySession.status == "partial",
                    StudySession.actual_duration > 0,
                )
            )
            or 0
        )
        cancelled_count = (
            self._db.scalar(
                select(func.count())
                .select_from(StudySession)
                .where(
                    StudySession.user_id == user_id,
                    StudySession.execution_state == "finished",
                    StudySession.status == "cancelled",
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
            shorter_count = sum(
                Decimal(item.actual_seconds)
                < Decimal(item.planned_minutes) * Decimal(60)
                for item in evidence
            )
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
            if shorter_count:
                observation = (
                    f"En {shorter_count} de {len(evidence)} sesiones, el tiempo "
                    "registrado fue menor que el planificado."
                )
            elif differences and (common_count > 1 or len(evidence) == 1):
                observation = (
                    f"En {common_count} de {len(evidence)} sesiones se registró "
                    f"cerca de {self._duration_label(common_actual)} frente a "
                    f"{self._duration_label(common_planned)} planificados."
                )
            elif differences:
                observation = (
                    f"El tiempo registrado difiere del planificado en {differences} "
                    f"de {len(evidence)} sesiones mostradas."
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
                    conclusion=observation,
                    observation=observation,
                    interpretation="",
                    uncertainty=(
                        "Los registros muestran la diferencia, pero no indican por "
                        "qué ocurrió ni bastan para concluir que sea un patrón estable."
                    ),
                    suggestion="",
                    interpretation_source="deterministic",
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
            insight, source = self._insight(
                user_id,
                evidence,
                differences,
                reviewed_count,
                on_gemini_request,
            )
            item = observations[0]
            item.interpretation = insight.interpretation
            item.suggestion = insight.suggestion
            item.interpretation_source = source
        return BehaviorAnalysisResponse(
            completed_session_count=completed_count,
            partial_session_count=partial_count,
            cancelled_session_count=cancelled_count,
            reviewed_session_count=reviewed_count,
            state="factual_summary" if observations else "insufficient_data",
            insufficient_data_guidance=(
                "Aún faltan sesiones finalizadas con duración registrada para "
                "comparar el tiempo planificado con el real. Las sesiones "
                "planificadas, incompletas y canceladas no permiten esa comparación."
            ),
            observations=observations,
        )

    def _insight(
        self,
        user_id: int,
        evidence: list[BehaviorEvidence],
        differences: int,
        reviewed_count: int,
        on_gemini_request: Callable[[], None] | None,
    ) -> tuple[BehaviorInsight, Literal["gemini", "deterministic", "fallback"]]:
        fallback = BehaviorInsight(
            interpretation=(
                "La diferencia puede ser relevante para valorar si la duración "
                "planificada representa bien el tiempo disponible para estudiar."
            ),
            suggestion=(
                "Podrías probar sesiones más breves y comparar los próximos "
                "registros para evaluar qué duración te resulta viable."
            ),
        )
        if not self._insight_generator or len(evidence) < 3 or not differences:
            return fallback, "deterministic"
        fingerprint = hashlib.sha256(
            json.dumps(
                [
                    user_id,
                    reviewed_count,
                    [
                        [
                            row.session_id,
                            row.planned_minutes,
                            row.actual_seconds,
                            row.result,
                            row.summary,
                        ]
                        for row in evidence
                    ],
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        now = time.monotonic()
        with self._CACHE_CONDITION:
            while fingerprint in self._CACHE_INFLIGHT:
                self._CACHE_CONDITION.wait(timeout=20)
                cached = self._CACHE.get(fingerprint)
                if cached and cached[0] > time.monotonic():
                    return cached[1], cached[2]
            cached = self._CACHE.get(fingerprint)
            if cached and cached[0] > now:
                return cached[1], cached[2]
            self._CACHE.pop(fingerprint, None)
            self._CACHE_INFLIGHT.add(fingerprint)
        result: BehaviorInsight
        source: Literal["gemini", "deterministic", "fallback"]
        try:
            if on_gemini_request:
                on_gemini_request()
            generated = self._insight_generator(
                json.dumps(
                    {
                        "registered_records": [
                            {
                                "planned_minutes": row.planned_minutes,
                                "actual_seconds": row.actual_seconds,
                                "result": row.result,
                                "context": row.summary,
                            }
                            for row in evidence
                        ],
                        "difference_count": differences,
                        "reviewed_count": len(evidence),
                    },
                    ensure_ascii=False,
                )
            )
            if (
                self._UNSAFE_TERMS.search(generated.interpretation)
                or self._UNSAFE_TERMS.search(generated.suggestion)
                or re.search(
                    r"\b(si fueron|si estabas probando|datos artificiales|"
                    r"sesiones de prueba|temporizador de prueba)\b",
                    generated.interpretation + " " + generated.suggestion,
                    re.IGNORECASE,
                )
                or re.search(r"\d", generated.interpretation + generated.suggestion)
            ):
                raise ValueError("Generated behavior insight failed safety checks")
            result, source = generated, "gemini"
        except Exception:
            result, source = fallback, "fallback"
        with self._CACHE_CONDITION:
            try:
                expired = [key for key, value in self._CACHE.items() if value[0] <= now]
                for key in expired:
                    self._CACHE.pop(key, None)
                if len(self._CACHE) >= self._MAX_CACHE_ENTRIES:
                    self._CACHE.pop(next(iter(self._CACHE)))
                self._CACHE[fingerprint] = (
                    time.monotonic() + self._CACHE_TTL_SECONDS,
                    result,
                    source,
                )
            finally:
                self._CACHE_INFLIGHT.discard(fingerprint)
                self._CACHE_CONDITION.notify_all()
        return result, source

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
