# Cognova — Contrato API v1

La generación Gemini de la rama `feat/gemini-behavior` y el primer análisis
de comportamiento se definen en
[AI_GENERATION_CONTRACT](AI_GENERATION_CONTRACT.md). Las nuevas rutas conservan
auth, onboarding, ownership, errores seguros y `no-store` de esta API.

## Alcance vigente

Materias, Actividades, Sesiones de Estudio + temporizador y Calendario están cerrados
en Backend. Database producción está en `0007_study_plans_and_challenges`; el pin
está en tools/database-ref.json. Calendario es de solo lectura sobre Actividades y
Sesiones, según [CALENDAR_CONTRACT](CALENDAR_CONTRACT.md). Sesiones se rige por
[STUDY_SESSIONS_CONTRACT](STUDY_SESSIONS_CONTRACT.md). Planes y Retos se rigen por
[STUDY_PLANS_CONTRACT](STUDY_PLANS_CONTRACT.md); Gemini real sigue pendiente en
producción mientras se valida la rama `feat/gemini-behavior`, y ningún
endpoint declara generado por IA un Plan manual. La API de Planes/Retos está
desplegada en Backend `d9fff7c36e6a1c1c98079e9be225c1d273e0e9d0` sobre Database
0007. CI del merge y smoke autenticado productivo pasaron. Los flujos de
propuesta `ai` se probaron con fixtures sintéticos; Gemini real sigue pendiente.


Auth, onboarding y cuestionario siguen operativos. Las secciones de otros módulos
conservan planificación de producto, no endpoints desplegados.

Base:

```text
/api/v1
```

Formato de error:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Mensaje legible."
  }
}
```

Fechas y horas: ISO 8601.

Los recursos privados requieren autenticación salvo indicación contraria.

## Operación

- GET `/health`: público, `200 {"status":"ok"}`; liveness del proceso, no consulta DB.
- GET `/ready`: público, `200 {"status":"ready"}` si `SELECT 1` funciona y Alembic
  está en la revisión esperada; `503 {"error":{"code":"SERVICE_UNAVAILABLE",
  "message":"Servicio temporalmente no disponible."}}` si falla. No expone hosts,
  credenciales, versiones ni detalles internos. Ambos usan Cache-Control: no-store.

## Auth

Fuente de verdad detallada: `AUTH_CONTRACT.md`.

- POST `/auth/register`
- POST `/auth/login`
- GET `/auth/me`
- POST `/auth/refresh`
- POST `/auth/logout`
- GET `/auth/sessions`
- DELETE `/auth/sessions/{session_id}`

## Questionnaire

- GET `/questionnaire`
- POST `/questionnaire`
- PUT `/questionnaire`

Contrato vigente de onboarding y cuestionario: [ONBOARDING_CONTRACT.md](ONBOARDING_CONTRACT.md).
Incluye GET `/questionnaire/catalog`, GET `/questionnaire/history` y
PUT `/onboarding/academic-profile`. Los tres endpoints existentes se conservan.
Todas estas rutas requieren Bearer; permiten onboarding incompleto y solo operan
sobre el usuario autenticado. No reciben user_id. Materias, Actividades, Sesiones,
Calendario, Planes y Retos están definidos en sus contratos específicos.

## Subjects

- GET `/subjects`
- POST `/subjects`
- GET `/subjects/{id}`
- PUT `/subjects/{id}`
- DELETE `/subjects/{id}`

Contrato implementado de Materias: [SUBJECTS_CONTRACT](SUBJECTS_CONTRACT.md).
Incluye catálogo, filtros, paginación, archivo/reactivación y DELETE confirmado.
Ownership y onboarding completo obligatorios.

## Goals

- GET `/goals`
- POST `/goals`
- GET `/goals/{id}`
- PUT `/goals/{id}`
- DELETE `/goals/{id}`

`subject_id` puede ser opcional si así lo define `DATA_MODEL.md`.

## Activities

Contrato vigente: [ACTIVITIES_CONTRACT](ACTIVITIES_CONTRACT.md), sobre 0005.
CRUD, PATCH de estado/deadline, historial persistente y filtros paginados.
La especificación anterior de type y /prioritized queda fuera de esta fase.

## Calendar

GET `/calendar`: rango obligatorio, filtro de tipo y filtros/paginación según
[CALENDAR_CONTRACT](CALENDAR_CONTRACT.md). Solo lectura de Actividades y Sesiones;
no eventos libres ni mutaciones propias. El orden es cronológico con desempate
estable por tipo e ID.

## Dependencies

Las dependencias entre Actividades se declaran dentro del criterio de generación
de un Reto bajo un Plan y se validan como acíclicas. No existe un módulo ni tabla
independiente `/dependencies` en esta entrega.

## Sessions

Contrato implementado y desplegado según
[STUDY_SESSIONS_CONTRACT](STUDY_SESSIONS_CONTRACT.md), sobre 0006_study_sessions.

- GET /sessions
- POST /sessions
- GET /sessions/{id}
- PUT /sessions/{id} — solo planificación sin iniciar
- DELETE /sessions/{id}?confirm=true — solo plan sin ejecución
- POST /sessions/{id}/start
- POST /sessions/{id}/pause
- POST /sessions/{id}/resume
- POST /sessions/{id}/finish

Bearer, onboarding completo, ownership, no-store, filtros, paginación,
transiciones y DTOs están definidos en el contrato específico.

## Analytics

- GET `/analytics/summary`
- GET `/analytics/by-time-of-day`
- GET `/analytics/by-duration`
- GET `/analytics/by-subject`

Con menos de 5 sesiones válidas:
- puede devolver datos descriptivos;
- no debe presentar patrones como concluyentes.

## History

- GET `/history`

Debe permitir reconstruir evolución cronológica del usuario.

La paginación/filtros concretos deben documentarse antes de implementar si no están definidos todavía.

## Streak

- GET `/streak`

Respuesta conceptual:
- current_streak
- best_streak

## AI

- POST `/ai/analyze`
- GET `/ai/conversations`
- POST `/ai/conversations`
- GET `/ai/conversations/{id}/messages`
- POST `/ai/conversations/{id}/messages`

Reglas:
- IA real;
- contexto académico;
- evidencia desde backend;
- rate limiting/cost controls;
- manejo de proveedor no disponible.

## Observations

- GET `/observations`
- GET `/observations/{id}`
- PATCH `/observations/{id}/feedback`

Feedback debe poder expresar:
- aceptación/rechazo;
- contexto;
- periodo atípico;
- exclusión justificada de futuros análisis cuando el dominio lo permita.

## Challenges

Los Retos viven dentro de Planes; no existe `/challenges` independiente. Ver
[STUDY_PLANS_CONTRACT](STUDY_PLANS_CONTRACT.md).

## Study Plans

Contrato vigente según [STUDY_PLANS_CONTRACT](STUDY_PLANS_CONTRACT.md).
Incluye Planes, decisiones de usuario y Retos anidados. La generación Gemini es
un proveedor futuro; hasta conectarlo, solo se crean Planes y Retos manuales.

## Profile

Datos académicos: PUT `/onboarding/academic-profile` según ONBOARDING_CONTRACT.md.
Lectura y estado en `/auth/me`. Nombre/email no se editan en esta fase. Los futuros
módulos académicos requieren get_onboarded_user, con403 ONBOARDING_REQUIRED cuando
el perfil o cuestionario inicial no estén completos. Auth/onboarding no lo exigen.

## DTOs y paginación

Este archivo fija rutas y reglas de dominio.

Antes de implementar cualquier endpoint que todavía no tenga request/response exactos:
1. definir DTO;
2. definir status codes;
3. definir errores;
4. definir paginación/filtros si aplica;
5. actualizar este contrato local y coordinar los repositorios afectados;
6. implementar backend;
7. consumir desde frontend.

No inferir un DTO público directamente de una tabla SQLAlchemy.
