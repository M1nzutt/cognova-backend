# Generación de Planes, observaciones y acompañamiento académico — contrato Backend

Modelo configurable mediante `GEMINI_MODEL`, usando SDK oficial `google-genai`
para Python. Sin variable se conserva `gemini-3.8-flash`; la opción validada
para las pruebas locales de Planes es `gemini-3.5-flash-lite`.
El código fuente actual exige Database `0010_nullable_password_hash`, pero el pin
de tooling `tools/database-ref.json` aún selecciona 0009; alinea el pin antes de
validar este contrato de extremo a extremo. Producción se documentó suspendida en
0007 y no se revalidó en este corte. Solo Backend envía datos al proveedor. Todas
las rutas exigen Bearer, onboarding completo y
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

`target_id` es nullable y genérico; si está presente debe corresponder al destino
tipado (`subject_id`, `activity_id` o `session_id`) y al `target_type`. La
instrucción al proveedor pide `target_id=null` para evitar duplicar enlaces; las
relaciones tipadas siguen siendo obligatorias y se validan antes de persistir.

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
  "completed_session_count": 3,
  "partial_session_count": 1,
  "cancelled_session_count": 1,
  "reviewed_session_count": 4,
  "state": "factual_summary",
  "insufficient_data_guidance": "Aún faltan registros para comparar.",
  "observations": [{
    "conclusion": "En 3 de 4 sesiones, el tiempo registrado fue menor que el planificado.",
    "observation": "En 3 de 4 sesiones, el tiempo registrado fue menor que el planificado.",
    "interpretation": "Una comparación puede ayudar a ajustar la duración prevista.",
    "uncertainty": "Los registros no indican por qué ocurrió.",
    "suggestion": "Podrías probar sesiones más breves y evaluar los próximos resultados.",
    "interpretation_source": "deterministic",
    "evidence": [{
      "session_id": 1,
      "planned_minutes": 25,
      "actual_seconds": "600",
      "result": "completed",
      "summary": "Biología: 25 min planificados"
    }],
    "question": "¿Qué contexto ayudaría a entender esta diferencia?",
    "confidence_basis": "La muestra incluye sesiones completadas y parciales.",
    "related_resources": [{
      "kind": "session",
      "id": 1,
      "label": "Biología · 01/01 12:00",
      "href": "/app/sessions/1"
    }]
  }]
}
```

Cuenta por separado sesiones completadas, parciales y canceladas. Solo compara
duración de sesiones finalizadas `completed` o `partial` con duración real
positiva; las canceladas no se incluyen en la comparación. La interpretación
marca si fue `gemini`, `deterministic` o `fallback`; las respuestas de Gemini
se validan y no se persisten como hechos. No se inventan causas ni se hacen
excepciones por cuenta.

En el contexto de Planes, `actual_minutes` expresa minutos: `actual_duration`
persistido en Sesiones está en segundos y se divide por 60. Una Sesión cancelada
aporta cero minutos de estudio; el tiempo de su temporizador se conserva en
`cancelled_elapsed_minutes`, identificado como excluido, para no transformarlo
en evidencia de estudio.

## Errores y límites

- 401/403/404/409/422 conservan las reglas existentes.
- 429 `TOO_MANY_REQUESTS`: cuota compartida para llamadas costosas; header
  `Retry-After`. Un 429 del proveedor se traduce a `503 GEMINI_RATE_LIMIT` con
  `Retry-After` corto, sin filtrar detalles internos.
- 503 `STUDY_PLAN_GENERATION_UNAVAILABLE`: falta de clave, timeout, 500/503,
  respuesta vacía, JSON o esquema inválido, o salida insegura del modelo.
- El proveedor usa timeout sin reintentos automáticos ni continuación:
  una operación solicita una sola generación. Para Observaciones, las reglas
  locales producen una interpretación `deterministic`; si Gemini falla o una
  respuesta no supera las validaciones, se usa una interpretación `fallback`.
- Las operaciones registran request id, nombre, duración, modelo y resultado
  general. Nunca prompts completos, datos académicos crudos, tokens ni clave.

La salida estructurada restringe el formato; validación Pydantic y reglas de
dominio Backend deciden si se acepta. Ningún texto del usuario puede autorizar
acceso a datos de otra cuenta ni saltarse estas reglas.

El snapshot y los logs seguros usan el modelo seleccionado en esa instancia
del proveedor, no una constante histórica. Cambiar `GEMINI_MODEL` afecta futuras
operaciones; no reescribe propuestas ni decisiones existentes.

## Acompañante académico escrito

Rutas autenticadas bajo `GET/POST /api/v1/academic-chat/conversations`,
`GET /api/v1/academic-chat/conversations/{id}/messages` y
`POST /api/v1/academic-chat/conversations/{id}/messages`. Exigen onboarding
completo; no reciben `user_id`. Una conversación pertenece a su creador y cada
mensaje se vincula con una FK compuesta `(user_id, conversation_id)`. Un recurso
ajeno se responde como 404. Lista hasta 50 conversaciones y páginas mensajes en
orden cronológico (50 por defecto, máximo 100).

El estudiante envía texto de 1–4000 caracteres; una cuenta puede tener 50
conversaciones y una conversación, 200 mensajes. El límite compartido PostgreSQL
protege las generaciones. Contexto acotado: últimas 12 intervenciones y 8000
caracteres de historial, datos estructurados del `AcademicContext` existente y
máximo 24000 bytes de entrada combinada. Gemini recibe como máximo 900 tokens de
salida. La clave solo existe en Backend.

El prompt trata como **datos no confiables** tanto los registros académicos como
el mensaje e historial; contenido recuperado no puede alterar las instrucciones
ni permitir acceso a otras cuentas. Solo admite las claves de `evidence_catalog`
que Backend construyó para ese estudiante. Las referencias se resuelven y validan
en Backend antes de guardar la respuesta; una clave inventada no se muestra.
Hechos, hipótesis y sugerencias se distinguen cuando aplican; se prohíben
diagnósticos, afirmaciones sin evidencia y modificaciones de recursos. Gemini no
tiene herramientas ni estado remoto (`store=false`, sin continuación ni reintento).

Los mensajes de estudiante y asistente se persisten. Un fallo del proveedor
conserva el mensaje del estudiante para que el historial no lo pierda, pero no
guarda una respuesta parcial o inválida. No hay endpoints de mutación académica
en el chat. Los logs contienen solo request id, operación, modelo, duración y
resultado general; nunca prompts, respuestas, historial ni claves.
