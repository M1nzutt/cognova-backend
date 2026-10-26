# Cognova — Contrato API v1

## Alcance vigente

Materias y Actividades están cerrados en Backend. Schema productivo: `0005_activities`.
Calendario v1 autorizado como vista transversal de solo lectura de Actividades.
Contrato: [CALENDAR_CONTRACT](CALENDAR_CONTRACT.md). Sin eventos libres, schema
nuevo ni implementación de Sesiones/Planes/Retos; futuras fuentes requieren contrato.

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
sobre el usuario autenticado. No reciben user_id. Materias y Actividades están implementados según sus
contratos; los restantes módulos son planificación futura.

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

GET `/calendar`: rango obligatorio, filtros y paginación según
[CALENDAR_CONTRACT](CALENDAR_CONTRACT.md). Solo lectura de Actividades;
no eventos libres ni mutaciones propias. Implementación en rama, aún no desplegada.

## Dependencies

- GET `/dependencies`
- POST `/dependencies`
- DELETE `/dependencies/{id}`

Representan dependencias reales entre actividades.

## Sessions

- GET `/sessions`
- POST `/sessions`
- GET `/sessions/{id}`
- DELETE `/sessions/{id}`
- POST `/sessions/{id}/start`
- POST `/sessions/{id}/pause`
- POST `/sessions/{id}/resume`
- POST `/sessions/{id}/finish`

El backend es la fuente de verdad del temporizador.

`finish` registra:
- resultado;
- motivo cuando corresponda;
- motivo personalizado opcional;
- contexto opcional.

Resultados:
- completed
- partial
- postponed
- cancelled

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

- GET `/challenges`
- POST `/challenges/{id}/accept`
- POST `/challenges/{id}/reject`
- POST `/challenges/{id}/complete`

Un reto aceptado no se edita.

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
