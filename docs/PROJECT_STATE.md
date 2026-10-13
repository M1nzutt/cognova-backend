# Cognova — Estado backend

Fase 2026-10-12: registro mínimo, perfil académico y cuestionario versionado.
Rama feat/onboarding-questionnaire; inicio limpio en 4d99685, 22 commits.
Trabajo anterior de runtime cerrado y publicado; se conserva como base de esta rama.
No se modifica main/Render/Netlify ni el repositorio database.

Database inspeccionado en copia tooling interna, SHA exacto:
232c43130c0fb3eddd32e1dd3707368ba0d87d4c. Head 0003_onboarding_questionnaire.
ORM nullable, archivo legacy y snapshots append-only; no copiar DDL al backend.
Contrato antes de código: ONBOARDING_CONTRACT.md y QUESTIONNAIRE.md.

Decisiones: onboarding calculado centralmente y expuesto en UserResponse;
perfil PUT dedicado; GET/POST/PUT questionnaire existentes, catálogo e historial
paginado; PUT con expected_revision y bloqueo de fila User para evitar pérdida.
Otro se codifica como prefijo other: dentro de string/array JSONB compatible con0003.
Registro usa solo name/email/password; login conserva compatibilidad de credenciales
antiguas. No se implementan módulos posteriores. Estado de implementación: en curso.

Validaciones completas y conteo final se registrarán al cerrar; CI PostgreSQL real
es obligatorio, sin presentar skips como integración. Commits pequeños y pushes
periódicos; objetivo global superar500 sin commits vacíos ni inflación artificial.
