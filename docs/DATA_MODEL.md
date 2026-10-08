# Cognova — Modelo de Datos

Este documento describe el modelo conceptual. `cognova-database` será la fuente
de verdad del esquema físico, Alembic, constraints, índices y cascadas.
El ORM utilizado para consultas permanece en `cognova-backend/app/models/`.
La copia local de migraciones se conserva temporalmente hasta el traspaso validado
de [DATABASE_HANDOFF.md](DATABASE_HANDOFF.md), sin modificar revisiones existentes.

Estado implementado: User, AuthSession y RateLimitBucket. Las entidades posteriores
son especificación de producto, no tablas que deban crearse en esta fase.

## Identidad y autenticación

### User
- id
- name
- email
- password_hash
- degree_program
- semester
- academic_goal
- created_at
- updated_at

Reglas:
- email único case-insensitive;
- password_hash nunca se expone.
- `academic_goal` permanece por compatibilidad con auth y la migración 0001.
  Conceptualmente pertenece a la pregunta 1 del cuestionario; su traslado requiere
  una tarea posterior con contrato y migración de datos, fuera de esta separación.

### AuthSession
- id
- user_id
- refresh_token_hash
- csrf_token_hash
- created_at
- expires_at
- last_used_at
- revoked_at

Reglas:
- una User tiene muchas AuthSession;
- refresh token plano nunca se persiste;
- sesión revocada no puede renovar ni validar access tokens ligados a su `sid`.

### RateLimitBucket (infraestructura implementada)
- key_hash (HMAC, clave primaria)
- hits
- expires_at (indexado)

Contadores compartidos de abuso en PostgreSQL; no almacenar IP/email en plano.
El modelo y las consultas permanecen en backend; el DDL de 0002 pasa a database.

## Onboarding

### Questionnaire
- id
- user_id
- answers_json
- created_at
- updated_at

Regla:
- una respuesta vigente por usuario salvo que más adelante se documente versionado.

## Organización académica

### Subject
- id
- user_id
- name
- description
- color
- created_at
- updated_at

### Goal
- id
- user_id
- subject_id?
- title
- description
- target_date
- status
- created_at
- updated_at

### AcademicActivity
- id
- user_id
- subject_id
- goal_id?
- title
- description
- type
- priority
- deadline
- status
- created_at
- updated_at

### ActivityDependency
- id
- user_id
- predecessor_activity_id
- successor_activity_id
- created_at

Reglas:
- ambas actividades deben pertenecer al mismo usuario;
- impedir dependencia de una actividad consigo misma;
- la API/grafo debe detectar ciclos cuando el dominio los prohíba.

## Sesiones y temporizador

### StudySession
- id
- user_id
- subject_id
- activity_id?
- planned_start
- planned_minutes
- timer_status
- result?
- reason?
- custom_reason?
- context_note?
- started_at?
- paused_at?
- finished_at?
- accumulated_seconds
- created_at
- updated_at

Estados de resultado:
- completed
- partial
- postponed
- cancelled

Estados de temporizador sugeridos:
- planned
- running
- paused
- finished

El backend es la fuente de verdad del tiempo acumulado.

### StudySessionInterval
- id
- session_id
- started_at
- ended_at?

Permite reconstruir periodos activos y auditar pausas/reanudaciones.

## IA e historial

### AIConversation
- id
- user_id
- created_at
- updated_at

### AIMessage
- id
- conversation_id
- role
- content
- metadata_json
- created_at

### AIObservation
- id
- user_id
- message
- evidence_json
- sample_size
- created_at
- user_feedback?
- excluded_from_future_analysis
- user_context?

### Reflection
- id
- user_id
- observation_id?
- message_id?
- text
- created_at

### Challenge
- id
- user_id
- title
- description
- evidence_json
- status
- start_date
- end_date
- result_note?
- created_at
- updated_at

Una vez aceptado, el contenido del reto no debe editarse.

## Racha

### StudyStreak
- id
- user_id
- current_streak
- best_streak
- last_valid_study_date
- updated_at

## Ownership

Toda entidad privada debe estar vinculada directa o indirectamente a un usuario.

El backend siempre deriva identidad del contexto autenticado; no confía en `user_id` arbitrario del cliente.

## Índices mínimos a evaluar

- `lower(users.email)` unique;
- foreign keys;
- `AuthSession.user_id`;
- `AuthSession.expires_at`;
- `StudySession.user_id + planned_start`;
- `AcademicActivity.user_id + deadline`;
- campos usados por filtros frecuentes.

Los índices finales deben justificarse con consultas reales.
