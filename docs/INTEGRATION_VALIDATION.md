# Validación de integración productiva

Fecha: 2026-10-17. Rama feat/onboarding-questionnaire. Release en curso.

## Runtime y permisos

Servicio existente srv-db2j6nqj9qps73crqa0g; main despliega automáticamente.
La configuración efectiva confirmó cognova_user propietario antes del cambio.
Se creó cognova_runtime y se actualizó únicamente DATABASE_URL del servicio.
Conexión real de ese rol confirma 0003 y permisos mínimos: SELECT/INSERT/UPDATE
users y auth_sessions; SELECT/INSERT/UPDATE/DELETE rate_limit_buckets; SELECT
alembic_version y user_academic_goal_legacy; SELECT/INSERT questionnaire_responses;
USAGE/SELECT users_id_seq y EXECUTE de las tres funciones de cuestionario/historia.
Sin CREATE public, ownership ni mutaciones de historia. Credencial no versionada.

## Validación previa

77 tests puros catálogo/codec/validación/registro pasan; Ruff pasa.
CI anterior 38349751140 certificó 226 tests (84 integración PostgreSQL), además
runtime wheel y launcher. No presentar esta evidencia como smoke productivo.
Consulta preliminar de readiness agotó timeout de 25s; no certifica estado HTTP.

## Pendiente

CI del nuevo commit, merge conservando historial, deploy y SHA Live.
Health/ready/OpenAPI/me sin sesión, smoke real de registro/login/perfil/cuestionario,
PUT con expected_revision, history, refresh/logout y sesiones. Verificar cookies,
CSRF, no-store. No se ha ejecutado el smoke ni creado usuarios en esta continuación.
