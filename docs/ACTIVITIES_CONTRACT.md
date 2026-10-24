# Actividades — contrato 2026-10-23

Base /api/v1/activities. Bearer, onboarding completo y no-store en todas las rutas.
No se modifica auth. Requests extra=forbid; propietario derivado del token.
Database: 604e296e2670d154ba7e18d7afa3f010e66dd42d, exactamente 0005_activities.
Este contrato sustituye la especificación conceptual anterior con type/goal_id;
no incluye priorización algorítmica, grafo, calendario, sesiones ni IA.

## DTOs

ActivityWrite (POST y PUT completo): title (NFC/strip, 1–50, sin controles),
subject_id (entero estricto positivo int32), deadline (ISO 8601 con zona obligatorio),
priority (low/medium/high/urgent), status (pending/in_progress/completed/postponed/cancelled),
estimated_duration (entero estricto 10–300), notes (string <=200 o null; omitido=null).
Fechas numéricas o sin zona rechazadas. No se exige fecha futura. Títulos repetidos
permitidos. Materias propias activas o archivadas admitidas; archivar no borra datos.
PUT sustituye los campos editables; nunca metadata/id/user_id. No es un PATCH.

ActivityResponse: id, subject_id, title, deadline, priority, status,
estimated_duration, notes, original_deadline, deadline_revision, created_at, updated_at.
Sin user_id. Timestamps ISO 8601. original_deadline/revision/timestamps los fija DB.
ListResponse: {items:[ActivityResponse],next_after_id:int|null}.
DeadlineEvent: revision, previous_deadline, new_deadline, event_type, occurred_at.
HistoryResponse: {items:[DeadlineEvent],next_after_revision:int|null}.

## Rutas

- POST /activities: ActivityWrite; 201 ActivityResponse.
- GET /activities: 200 ListResponse; filtros opcionales subject_id, status, priority,
  deadline (instante exacto), deadline_from y deadline_to (rango inclusivo).
  Se combinan por AND; from > to es 422. IDs positivos int32. limit=20 (1–100),
  after_id exclusivo; id ASC. Mantener filtros al paginar, sin snapshot entre páginas.
  Filtro de materia ajena/inexistente devuelve vacío, sin revelar existencia.
- GET /activities/{activity_id}: 200 ActivityResponse.
- PUT /activities/{activity_id}: ActivityWrite; 200 ActivityResponse.
- PATCH /activities/{activity_id}/status: {status,expected_status}; 200 ActivityResponse.
- PATCH /activities/{activity_id}/deadline: {deadline,expected_revision:int>=0};
  200 ActivityResponse. Revisión máxima int32; precondición contra deadline_revision.
- GET /activities/{activity_id}/deadline-history: limit=20 (1–100),
  after_revision positivo exclusivo; revision ASC; 200 HistoryResponse.
- DELETE /activities/{activity_id}?confirm=true: literal obligatorio; 204 sin cuerpo.

## Estados y conflictos

pending, in_progress y postponed pueden pasar a cualquier estado. completed y
cancelled solo pueden mantenerse o reabrirse a pending; otra transición da
409 ACTIVITY_TRANSITION_CONFLICT. El mismo estado es idempotente.
expected_status desactualizado da ACTIVITY_STATE_CONFLICT; expected_revision
incorrecto da ACTIVITY_DEADLINE_CONFLICT (ambos 409). PUT aplica la misma matriz;
sus campos son reemplazo deliberado del estado actual, sin precondición optimista.
Mover deadline no cambia status; declarar postponed no modifica deadline.

DB registra todo cambio de instante en la misma transacción: postponed si aumenta,
rescheduled si disminuye. Mismo instante/otro offset no crea evento. Conserva fecha
inicial y revisiones. Backend nunca inserta, modifica ni borra historia.
Una actividad con historia NO puede borrarse en 0005: 409 ACTIVITY_HAS_DEPENDENCIES.
También se aplica a FK futuras; nunca borrar dependencias para forzar DELETE.
Materia con cualquier actividad: 409 SUBJECT_HAS_DEPENDENCIES existente.

## Errores y transacciones

Formato global {error:{code,message}}, sin SQL ni payloads privados.
401 auth; 403 ONBOARDING_REQUIRED; 422 VALIDATION_ERROR para campos/query inválidos.
404 ACTIVITY_NOT_FOUND indistinguible para ajena/inexistente; lo mismo para
SUBJECT_NOT_FOUND al asignar materia. Propiedad de actividad se comprueba antes
que propiedad de nueva materia. 409 ACTIVITY_WRITE_CONFLICT tras agotar retries.
503 SERVICE_UNAVAILABLE para permisos/conectividad DB; sin reintentar commit ambiguo.

Toda mutación termina snapshot de auth y abre READ COMMITTED; lock users primero,
luego actividad propia FOR UPDATE. Serializa con Materias, conserva orden de locks,
relee estado en cada intento. Reintentos completos solo 40001/40P01, máximo tres.
FK compuesta garantiza mismo dueño incluso ante escrituras externas. Sin RLS:
las consultas de lectura/historia y escritura siempre restringen user_id.

## Dependencias

Frontend puede implementar contra contrato/OpenAPI validado en paralelo.
Producción requiere release Database 0005, respaldo/preflight y grants mínimos:
activities SELECT/INSERT/UPDATE/DELETE, activities_id_seq USAGE/SELECT,
activity_deadline_events solo SELECT; preservar permisos previos y lock users.
Sin DDL, INSERT/UPDATE/DELETE de historia ni EXECUTE de funciones trigger runtime.
No aplicar migraciones/grants productivos desde Backend. No merge/deploy en esta tarea.
