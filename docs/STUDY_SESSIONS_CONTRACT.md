# Sesiones de estudio — contrato API v1 (2026-11-02)

Este contrato consume el esquema productivo 0006_study_sessions. La API maneja
planificación y ejecución; no crea tablas ni cambia Database. Los recursos son del
usuario autenticado y todas las rutas exigen Bearer y onboarding completo. Nunca se
acepta user_id en el request o la respuesta. Las respuestas usan Cache-Control:
no-store mediante el middleware común.

## Recursos y DTO

La ruta base es /api/v1/sessions, distinta de /api/v1/auth/sessions.

Tokens:

- execution_state: planned, running, paused, finished.
- status: resultado final nullable: completed, partial, postponed, cancelled.
- context: nullable: finished_early, distracted, tired, interrupted,
  changed_activity, other.

StudySessionSummary expone id, subject_id, activity_id, planned_start_at,
planned_duration, execution_state, status, start_at, end_at, actual_duration,
context, created_at y updated_at. StudySessionDetail añade other_text e intervals,
ordenados por started_at,id; cada intervalo expone id, started_at y ended_at (null
mientras corre). No se expone user_id.

Todos los timestamps llevan zona y se serializan en ISO 8601. `actual_duration` es
una cadena JSON decimal de segundos con seis posiciones, suma de intervalos cerrados
(por ejemplo, `"0.000000"`). El intervalo
abierto se devuelve con su started_at; el servidor define sus límites al pausar
o finalizar. El cliente puede animar el intervalo vigente, pero debe reconciliarse
con cada respuesta del servidor. El plan de 10–180 minutos no limita la ejecución.

## Endpoints

- GET /sessions: filtros opcionales subject_id, activity_id, execution_state,
  status, planned_start_from inclusivo y planned_start_to exclusivo.
  limit entre 1 y 100 (default 50). Orden estable (planned_start_at,id).
  Cursor exclusivo con after_planned_start_at y after_id, ambos presentes o
  ambos ausentes. Responde {items:[StudySessionSummary],next_cursor:{...}|null}.
- POST /sessions: crea una planificación y responde 201 con detalle.
  Body estricto: subject_id, activity_id nullable opcional,
  planned_start_at y planned_duration.
- GET /sessions/{id}: detalle de sesión propia.
- PUT /sessions/{id}: reemplazo de los cuatro campos de planificación; solo
  funciona mientras siga planned y no tenga ejecución.
- DELETE /sessions/{id}?confirm=true: 204. Solo permite borrar una planificación
  aún planned, sin intervalos ni ejecución. El historial iniciado/finalizado no
  se purga desde esta API. Confirmación ausente o distinta de true: 422.
- POST /sessions/{id}/start: sin body. Fija start_at e inserta el primer
  intervalo con el mismo instante UTC.
- POST /sessions/{id}/pause: sin body. Cierra el intervalo abierto y actualiza
  actual_duration en la misma transacción.
- POST /sessions/{id}/resume: sin body. Abre otro intervalo; no altera los ya
  cerrados ni suma el tiempo de pausa.
- POST /sessions/{id}/finish: body estricto status, context nullable y
  other_text nullable. Cierra el intervalo si está abierto, fija end_at y la
  suma de segundos cerrados. completed y partial requieren ejecución positiva.
  Desde planned solo permite postponed o cancelled, sin timestamps ni
  intervalos de ejecución. El contexto personalizado solo corresponde a una
  ejecución; other_text es obligatorio (1–200, recortado, no blanco) con
  context=other, y se prohíbe en los demás casos.

Las escrituras responden con StudySessionDetail. El servidor genera los instantes
de inicio, pausa, reanudación y fin; no confía en horas de timer enviadas por el
cliente.

## Transiciones y concurrencia

planned -> running -> paused -> running -> finished
planned -> finished únicamente con resultado postponed o cancelled.
running/paused -> finished con cualquiera de los cuatro resultados.
finished es terminal.

Double start/pause/resume/finish, editar una sesión que dejó de estar planificada,
y comenzar otra sesión mientras existe una running o paused del usuario producen
409. Las mutaciones serializan por fila users en READ COMMITTED y bloquean la sesión
objetivo; restricciones únicas de 0006 siguen siendo la última defensa ante
carreras/escritores externos. Se reintenta la transacción completa de forma acotada
ante SQLSTATE 40001/40P01; no se reintenta un commit de resultado ambiguo.

Cada mutación actualiza ambas tablas cuando corresponde y confirma una sola
transacción. actual_duration se recalcula desde los intervalos cerrados como
segundos exactos hasta microsegundos; las pausas se excluyen. DB conserva identidad
e intervalos inmutables, FKs RESTRICT, no solapamiento, máximo un intervalo abierto,
y máximo una sesión activa por usuario. No hay triggers de timer ni lógica
automática de transición en DB.

La materia debe pertenecer al usuario autenticado. Si se envía activity_id, la
actividad debe pertenecer al mismo usuario y a esa misma materia. El ownership se
valida en el servicio y las FKs compuestas también lo protegen físicamente. Una
materia archivada conserva sus relaciones; este contrato no prohíbe programar en
ella.

## Errores y seguridad

- 401: Bearer ausente, inválido o revocado.
- 403 ONBOARDING_REQUIRED: perfil/cuestionario incompleto.
- 404 STUDY_SESSION_NOT_FOUND: sesión ajena o inexistente, respuesta indistinguible.
- 404 SUBJECT_NOT_FOUND / ACTIVITY_NOT_FOUND: relación ajena o inexistente.
- 409 STUDY_SESSION_TRANSITION_CONFLICT: acción no válida para el ciclo actual.
- 409 STUDY_SESSION_ACTIVE_CONFLICT: ya hay otra sesión running/paused.
- 409 STUDY_SESSION_HISTORY_CONFLICT: borrado impediría perder ejecución/historial.
- 409 STUDY_SESSION_WRITE_CONFLICT: contención concurrente agotó reintentos.
- 422 VALIDATION_ERROR: campos, límites, enums, fechas o confirmación inválidos.
- 503 SERVICE_UNAVAILABLE: fallo de PostgreSQL; sin SQL ni detalles internos.

Filtros de listados siempre incluyen user_id del Bearer; filtrar por una materia o
actividad ajena devuelve lista vacía. Auth, cookies, CSRF y rate limiting existentes
no cambian. Los endpoints de sesión usan Bearer; el middleware global aplica
no-store a éxito y error. Calendario conserva su contrato v1 de solo Actividades:
planned_start_at queda definido como fecha canónica para una futura ampliación
explícita, sin cambiar ahora su endpoint, DTO ni Frontend.

## Responsabilidades

- DB: integridad física y evidencia persistente según 0006_study_sessions.
- Backend: autorización, onboarding, validación de relaciones, transiciones,
  serialización, temporizador, timestamps de ejecución y cálculo de duración.
- Calendario/Frontend: quedan fuera de este bloque.
