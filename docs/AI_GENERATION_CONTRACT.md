# Generación de Planes y observaciones académicas — contrato Backend

Modelo: `gemini-3.8-flash` mediante SDK oficial `google-genai` para Python.
La rama Backend fija Database `0008_ai_plan_proposal_snapshot` en
`tools/database-ref.json`; producción permanece suspendida en 0007. Solo Backend envía
datos al proveedor. Todas las rutas exigen Bearer, onboarding completo y
ownership; `Cache-Control: no-store`. La clave `GEMINI_API_KEY` vive únicamente
en el entorno del proceso Backend.

## POST /api/v1/study-plans/generate

Sin body. El servicio recopila únicamente registros académicos del usuario
autenticado y envía una muestra acotada. Responde `201` con:

```json
{
  "plan": { "id": 1, "source": "ai", "status": "draft" },
  "explanation": "Por qué se propone este recorrido.",
  "reasoning_summary": "Resumen breve basado en registros propios."
}
```

`plan` es el `StudyPlanDetail` vigente completo; el ejemplo omite sus otros
campos. El proveedor devuelve y Backend valida `name`, `objective`, `start_date`,
`end_date`, `explanation`, `subject_ids`, `activity_ids`, `session_ids`,
`proposed_challenges` y `reasoning_summary`. Las fechas se convierten a
`start_at`/`end_at` con zona. IDs duplicados, inexistentes, ajenos o incoherentes,
fechas inválidas y retos sin evidencia invalidan toda la propuesta. Cada cita
de evidencia debe ser una clave exacta del catálogo de hechos que Backend
construyó desde recursos propios; se rechazan claves inventadas. No se
crean ni modifican Materias, Actividades o Sesiones. El Plan nace `ai/draft`;
los Retos propuestos nacen `ai/pending` y solo dentro de ese Plan.

Backend guarda en `study_plans.ai_proposal_snapshot` la propuesta visible vigente
con `schema_version=1`, modelo, fecha de generación, explicación, resumen, Plan
original y Retos propuestos. El detalle devuelve el snapshot y proyecta
`explanation`/`reasoning_summary` desde esa fila después de refresh. No incluye
chain-of-thought, prompts completos, salida cruda del proveedor ni secretos.
El tamaño se verifica antes de escribir con `octet_length(jsonb::text) <= 32768`;
un exceso devuelve 503 seguro sin Plan ni Retos parciales. Los Planes manuales
y los IA históricos sin snapshot mantienen `NULL`.

## POST /api/v1/study-plans/{id}/regenerate

Solo propuesta `ai/draft` propia. Mantiene el contrato `StudyPlanDetail` de
respuesta. Solicita otra salida real; la valida íntegra antes de modificar.
El registro `regenerated` conserva el snapshot previo en `proposed_value` y
`chosen_value=null`; el snapshot nuevo queda vigente en el Plan. Antes de escribir,
Backend comprueba el límite de 32768 bytes del snapshot nuevo y el de 65536 bytes
de `proposed_value` usando la serialización exacta de PostgreSQL. Si un Plan IA
histórico tiene snapshot `NULL`, guarda como evidencia su estado/Retos 0007 sin
atribuirle una explicación inexistente. Los nuevos recursos se aplican únicamente
al borrador de propuesta; el usuario aún debe aceptar, editar o rechazar.
Un fallo del proveedor o una respuesta inválida no escribe Plan, Retos ni
decisiones. Los Retos existentes con historia que impedirían reemplazo seguro
producen `409 STUDY_PLAN_HISTORY_CONFLICT` antes de llamar al proveedor.

## POST /api/v1/analysis/behavior

Sin body. Respuesta de solo lectura:

```json
{
  "finished_session_count": 5,
  "pattern_eligible": true,
  "observations": [{
    "observation": "Descripción o hipótesis, expresada con cautela.",
    "evidence": ["Hecho verificable con cantidad y contexto."],
    "question": "¿Cómo interpretas esta diferencia?",
    "confidence_basis": "Muestra y límites de la evidencia.",
    "related_subject_ids": [],
    "related_activity_ids": [],
    "related_session_ids": []
  }]
}
```

Cuenta solo Sesiones `finished` con resultado `completed` o `partial` y
duración real positiva para el umbral de cinco. Con 0–4, Backend devuelve
hechos deterministas y preguntas sin afirmar patrones ni llamar al modelo.
Con al menos cinco, Gemini puede proponer hipótesis en forma de pregunta,
validadas contra IDs propios y evidencia proporcionada. No se persisten
inferencias como hechos. La salida no diagnostica ni atribuye causas
psicológicas.

## Errores y límites

- 401/403/404/409/422 conservan las reglas existentes.
- 429 `TOO_MANY_REQUESTS`: cuota compartida para llamadas costosas; header
  `Retry-After`. Un 429 del proveedor se traduce a `503 GEMINI_RATE_LIMIT` con
  `Retry-After` corto, sin filtrar detalles internos.
- 503 `STUDY_PLAN_GENERATION_UNAVAILABLE`: falta de clave, timeout, 500/503,
  respuesta vacía, JSON o esquema inválido, o salida insegura del modelo.
- El proveedor usa timeout y, como máximo, un reintento conservador para
  errores transitorios inequívocos antes de cualquier escritura.
- Las operaciones registran request id, nombre, duración, modelo y resultado
  general. Nunca prompts completos, datos académicos crudos, tokens ni clave.

La salida estructurada restringe el formato; validación Pydantic y reglas de
dominio Backend deciden si se acepta. Ningún texto del usuario puede autorizar
acceso a datos de otra cuenta ni saltarse estas reglas.
