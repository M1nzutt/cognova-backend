# Cognova — Contrato API v1

Base: `/api/v1`

## Auth
- POST `/auth/register`
- POST `/auth/login`

## Questionnaire
- GET `/questionnaire`
- POST `/questionnaire`

## Subjects
- GET `/subjects`
- POST `/subjects`
- GET `/subjects/{id}`
- PUT `/subjects/{id}`
- DELETE `/subjects/{id}`

## Goals
- GET `/goals`
- POST `/goals`
- GET `/goals/{id}`
- PUT `/goals/{id}`
- DELETE `/goals/{id}`

## Activities
- GET `/activities`
- POST `/activities`
- GET `/activities/{id}`
- PUT `/activities/{id}`
- DELETE `/activities/{id}`
- GET `/activities/prioritized`

## Sessions
- GET `/sessions`
- POST `/sessions`
- GET `/sessions/{id}`
- DELETE `/sessions/{id}`
- POST `/sessions/{id}/start`
- POST `/sessions/{id}/pause`
- POST `/sessions/{id}/resume`
- POST `/sessions/{id}/finish`

## Analytics
- GET `/analytics/summary`
- GET `/analytics/by-time-of-day`
- GET `/analytics/by-duration`
- GET `/analytics/by-subject`

## History
- GET `/history`

## Streak
- GET `/streak`

## AI
- POST `/ai/analyze`
- GET `/ai/conversations`
- POST `/ai/conversations`
- GET `/ai/conversations/{id}/messages`
- POST `/ai/conversations/{id}/messages`

## Observations
- GET `/observations`
- GET `/observations/{id}`
- PATCH `/observations/{id}/feedback`

## Challenges
- GET `/challenges`
- POST `/challenges/{id}/accept`
- POST `/challenges/{id}/reject`
- POST `/challenges/{id}/complete`

## Dependencies
- GET `/dependencies`
- POST `/dependencies`
- DELETE `/dependencies/{id}`

## Error estándar
```json
{"error":{"code":"ERROR_CODE","message":"Readable message"}}
```

Fechas: ISO 8601. Auth: Bearer JWT.
