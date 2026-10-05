# Cognova — Contrato API v1

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

Reglas:
- onboarding obligatorio después de registro;
- las preguntas/opciones salen de `QUESTIONNAIRE.md`;
- no inventar opciones desde frontend.

## Subjects

- GET `/subjects`
- POST `/subjects`
- GET `/subjects/{id}`
- PUT `/subjects/{id}`
- DELETE `/subjects/{id}`

Ownership obligatorio.

## Goals

- GET `/goals`
- POST `/goals`
- GET `/goals/{id}`
- PUT `/goals/{id}`
- DELETE `/goals/{id}`

`subject_id` puede ser opcional si así lo define `DATA_MODEL.md`.

## Activities

- GET `/activities`
- POST `/activities`
- GET `/activities/{id}`
- PUT `/activities/{id}`
- DELETE `/activities/{id}`
- GET `/activities/prioritized`

Debe soportar:
- `type`;
- `priority`;
- `deadline`;
- estado.

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

Con menos de 5 sesiones:
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

Si se necesita edición de perfil, el agente debe documentar primero el contrato exacto y sincronizar ambos repos antes de implementarlo.

## DTOs y paginación

Este archivo fija rutas y reglas de dominio.

Antes de implementar cualquier endpoint que todavía no tenga request/response exactos:
1. definir DTO;
2. definir status codes;
3. definir errores;
4. definir paginación/filtros si aplica;
5. actualizar este contrato en ambos repos;
6. implementar backend;
7. consumir desde frontend.

No inferir un DTO público directamente de una tabla SQLAlchemy.
