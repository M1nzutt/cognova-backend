# Contrato de Planes de Estudio y Retos

Versión API: `/api/v1`. Persistencia: Database `0007_study_plans_and_challenges`.
Este contrato es de Backend; Database conserva la autoridad de DDL.
La extensión Gemini de la rama fija Database `0008_ai_plan_proposal_snapshot`;
producción suspendida sigue en 0007 y no sirve esa extensión todavía.

## Reglas transversales

- Las rutas requieren Bearer, onboarding completo y ownership por el usuario
  autenticado. Ningún request o response acepta/expone `user_id`.
- Las respuestas usan `Cache-Control: no-store`. Mutaciones conservan CSRF,
  transacciones y bloqueo por usuario del Backend.
- Un Plan referencia Materias, Actividades y Sesiones existentes; nunca copia ni
  cambia esos recursos. Sesiones asociadas conservan su Materia y Actividad.
- Planes y Retos son privados del Plan. No existe CRUD independiente de Retos ni
  una tabla de dependencias de Actividades.
- `POST /study-plans` conserva la creación manual. La rama
  `feat/gemini-behavior` añade propuestas reales mediante
  `POST /study-plans/generate`; sin `GEMINI_API_KEY` del proceso Backend,
  generación y regeneración devuelven `503 STUDY_PLAN_GENERATION_UNAVAILABLE`.
  Contrato de salida y límites: [AI_GENERATION_CONTRACT](AI_GENERATION_CONTRACT.md).
- Ningún contenido generado se aplica a recursos académicos. El usuario acepta,
  edita o rechaza una propuesta explícitamente.

## Planes

Estados: `draft`, `active`, `completed`, `abandoned`. Fuente: `ai` o `manual`;
`POST /study-plans` crea `manual`; `POST /study-plans/generate` crea `ai/draft`.

### Rutas

- `GET /study-plans?status=&limit=&after_id=` — cursor ascendente por ID;
  `status` admite los cuatro estados y `all`. `limit` va de 1 a 100.
- `POST /study-plans` — crea un Plan manual en `draft`.
- `POST /study-plans/generate` — crea una propuesta `ai/draft` desde registros
  propios, con Retos `ai/pending` solo si existe evidencia verificable.
- `GET /study-plans/{id}` — detalle, recursos existentes, historial de decisiones
  y proyecciones algorítmicas del Plan. En la rama Gemini añade snapshot IA
  vigente y explicación/resumen derivados de la fila persistida.
- `PUT /study-plans/{id}` — reemplaza nombre, objetivo, fechas y relaciones; solo
  en Plan `draft`. Registra cada cambio del usuario como decisión `edited`.
- `DELETE /study-plans/{id}?confirm=true` — solo Plan manual `draft` sin relaciones,
  decisiones ni Retos; preserva historial con RESTRICT.
- `POST /study-plans/{id}/accept` — solo propuesta `ai` en `draft`; guarda `accepted`
  con propuesta y elección del usuario, y activa el Plan.
- `POST /study-plans/{id}/reject` — solo propuesta `ai` en `draft`; guarda `rejected`
  y abandona el Plan.
- `POST /study-plans/{id}/regenerate` — solicita una nueva propuesta al proveedor;
  valida y aplica el borrador nuevo en una transacción. Conserva la propuesta
  anterior en una decisión `regenerated`; un fallo no escribe nada.
- `POST /study-plans/{id}/activate` — Plan manual `draft` a `active`.
- `POST /study-plans/{id}/complete` — Plan `active` a `completed`.
- `POST /study-plans/{id}/abandon` — Plan `draft` o `active` a `abandoned`.
- `POST /study-plans/{id}/undo` — deshace el último cambio `edited` en un Plan
  `draft`; agrega una decisión inversa y no borra evidencia histórica.

Estados terminales `completed` y `abandoned` no se reabren. Cambios de estado no
editan ni borran Actividades, Sesiones o Materias.

### Escritura y respuesta

`POST`/`PUT` aceptan `name` (1–100), `objective` (1–2000), `start_at`, `end_at`
ISO 8601 con zona horaria, `subject_ids` (0–100), `activity_ids` (0–200) y
`study_session_ids` (0–200). IDs positivos y sin duplicados; `end_at > start_at`.
Las Materias deben ser del usuario. Cada Actividad y Sesión debe ser del usuario y
su Materia debe pertenecer al Plan. Si una Sesión referencia Actividad, el Plan
debe incluir esa Actividad con la misma Materia. La Sesión planificada debe caber
en `[start_at, end_at)`.

La lista devuelve `items` y `next_after_id` nullable. El detalle devuelve los
campos del Plan, resúmenes de recursos originales, `decisions`, `challenge_count`,
`hierarchy`, `priority_order`, `activity_dependency_order`, `weekly_rhythm` y
`candidate_slots` y `schedule_conflict`. Las proyecciones no se persisten y no copian recursos.
`candidate_slots` significa espacio no ocupado por Sesiones del Plan; no afirma
disponibilidad personal ni consulta calendarios externos.
`ai_proposal_snapshot`, `explanation` y `reasoning_summary` son nullable. Los
Planes manuales y Planes IA antiguos sin snapshot devuelven NULL. El snapshot
v1 conserva la propuesta original visible y sus Retos; editar, aceptar o
rechazar no lo sobrescribe. Regenerate copia el anterior a `proposed_value` y
guarda uno nuevo solo tras validación completa y límites JSONB 32768/65536 bytes.
Si dos Sesiones existentes se solapan, se conservan ambas relaciones y el detalle
indica `schedule_conflict: true` con `candidate_slots` vacío. Vincularlas no las edita.

`study_plan_decisions` registra `accepted`, `edited`, `rejected` y `regenerated`.
Para `edited` se conservan `field_path`, `proposed_value` y `chosen_value`; aceptar
y rechazar conservan la propuesta completa. La historia es append-only. Undo añade
una decisión inversa con `field_path` `undo:<decision_id>:<campo>` para identificar
qué edición original revierte y permitir deshacer cambios anteriores sin borrar filas.

## Retos

Estados: `pending`, `in_progress`, `completed`, `failed`, `cancelled`. Fuente
creada: `manual`; criterios de generación deben ser JSON objeto no vacío. Los
Retos son contextuales y pueden asociar Materia, Actividad y/o Sesión del mismo
Plan y usuario. No se aceptan IDs que solo existan fuera del Plan.

`target_type` admite:

- `study_minutes`: `{ "minutes": 1..1440 }`, con Materia o Sesión;
- `activity_completion`: `{ "status": "completed" }`, con Actividad;
- `session_completion`: `{ "lifecycle": "finished" }`, con Sesión;
- `subject_mastery`: `{ "criterion": "...", "threshold": 1..100 }`, con Materia;
- `custom`: objeto JSON no vacío de hasta 4096 bytes.

`start_at` y `deadline` son nullable; si existen, `deadline >= start_at`.
`depends_on_activity_ids` se conserva en `generation_criteria` y solo puede
referirse a Actividades ya vinculadas al mismo Plan. Backend valida ciclos antes
de aceptar una relación.

### Rutas

- `GET /study-plans/{id}/challenges?limit=&after_id=`
- `POST /study-plans/{id}/challenges`
- `GET /study-plans/{id}/challenges/{challenge_id}`
- `PUT /study-plans/{id}/challenges/{challenge_id}` — solo `pending`.
- `POST /study-plans/{id}/challenges/{challenge_id}/start` — `pending` a
  `in_progress`.
- `POST /study-plans/{id}/challenges/{challenge_id}/complete` — `in_progress` a
  `completed`.
- `POST /study-plans/{id}/challenges/{challenge_id}/fail` — `in_progress` a
  `failed`.
- `POST /study-plans/{id}/challenges/{challenge_id}/cancel` — `pending` o
  `in_progress` a `cancelled`.

Los estados terminales no se reabren. No existe DELETE porque el runtime Database
no tiene ese privilegio para Retos; se conserva la historia.

## Errores

- `401 AUTHENTICATION_REQUIRED`, `403 ONBOARDING_REQUIRED`, `404
  STUDY_PLAN_NOT_FOUND` o `404 STUDY_CHALLENGE_NOT_FOUND` para inexistente/ajeno,
  `422 VALIDATION_ERROR`, `503 SERVICE_UNAVAILABLE` son comunes.
- `409 STUDY_PLAN_STATE_CONFLICT`: estado incompatible con la acción.
- `409 STUDY_PLAN_RESOURCE_CONFLICT`: recurso no vinculado o contexto incoherente.
- `409 STUDY_PLAN_WRITE_CONFLICT`: conflicto recuperable de escritura agotado.
- `409 STUDY_PLAN_DEPENDENCY_CONFLICT`: dependencia duplicada, ajena o cíclica.
- `409 STUDY_PLAN_HISTORY_CONFLICT`: borrar/editar violaría historia conservada.
- `409 STUDY_CHALLENGE_STATE_CONFLICT`: transición de Reto inválida.
- `409 STUDY_CHALLENGE_TARGET_CONFLICT`: objetivo no compatible con su contexto.
- `503 STUDY_PLAN_GENERATION_UNAVAILABLE`: falta proveedor/clave o su salida es
  inválida o temporalmente no disponible.
- `503 GEMINI_RATE_LIMIT`: cuota del proveedor agotada; incluye `Retry-After`.

La envoltura de error es `{ "error": { "code": "...", "message": "..." } }`.
