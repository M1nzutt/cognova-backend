# Cognova — Estado backend

## Materias — 2026-10-18

Rama feat/subjects-0004, inicio limpio dec1f73, 57 commits. Contrato definido en
SUBJECTS_CONTRACT.md antes de implementación. Pin y readiness actualizados a
c3394c38c55a8cd466d10f02fe7c80d7c1e1980f / 0004_subjects; ORM y DTOs separados.
26 pruebas DTO/readiness y 3 PostgreSQL de compatibilidad ORM/startup/readiness
aprobadas. DTOs y catálogo: 19 pruebas propias aprobadas (normalización NFC,
límites, tipos estrictos, campos prohibidos y todas las combinaciones de color).
Servicio transaccional validado: 7 pruebas unitarias de rollback/reintento,
traducción de constraints y rechazo de reintento ante commit ambiguo; 20 casos
PostgreSQL de Materias aprobados. Rutas y OpenAPI publicados: CRUD, catálogo,
filtros/cursor, archivo/reactivación y DELETE con confirm=true; Bearer + onboarding
completo. Prueba de rutas existentes actualizada para reconocer el módulo real.
Suite ampliada completa y validaciones de empaquetado en curso.
Sin cambios de auth,
producción ni repositorios hermanos. El historial de onboarding sigue debajo.


Release productivo: 2026-10-17. Rama main. Historial de implementación abajo.
Implementado: registro mínimo → datos académicos → percepción inicial → onboarding.
Onboarding desplegado en el servicio Render existente. No se modificaron frontend ni database.

## Release operativo 2026-10-17 — desplegado

Database ya aplicó 0003 y preservó sus datos. Servicio Render existente confirmado:
srv-db2j6nqj9qps73crqa0g, rama main, autoDeploy=yes. Merge sin squash y SHA Live:
9309effdd1b71acc3fe5e24bc8c19b70c3d8c0c8; deploy dep-db9vrie7bikc73e676q0.
La DATABASE_URL efectiva usaba cognova_user propietario. Se creó cognova_runtime
sin ownership/CREATE/superuser/CREATEDB/CREATEROLE; se actualizó solo DATABASE_URL
en Render, manteniendo destino interno y configuración restante. Contraseña
aleatoria SCRAM, únicamente en memoria y secret Render; nunca en Git/logs.
Permisos verificados con esa credencial sobre 0003: users/auth_sessions SELECT,
INSERT,UPDATE; buckets también DELETE; alembic_version/legacy solo SELECT;
questionnaire_responses SELECT,INSERT; secuencia users USAGE/SELECT y funciones
EXECUTE. Sin UPDATE/DELETE de historia ni CREATE en public. Migrador sin cambios.
Smoke ampliado en scripts/smoke_auth.py para onboarding/historial y no-store,
Secure/HttpOnly/SameSite/host-only. 77 pruebas puras pasan y Ruff correcto.
CI previo 39077069939 success: 226 tests sin skips, launcher adicional, mypy/build/
audit/gitleaks aprobados. Smoke real completo aprobado: health/ready/OpenAPI 200,
me sin sesión 401, registro mínimo, login, me, perfil, catálogo, POST/GET/PUT,
historial, refresh, sesiones y logout. expected_revision viejo devuelve 409;
baseline intacto. Cookies/CSRF/no-store correctos. Verificación DB READ ONLY:
una cuenta sintética retenida, dos snapshots (1/2), dos sesiones revocadas, cero
activas. No borrar historial sintético. Frontend puede desplegar su versión
compatible con el contrato; su navegador/proxy/E2E sigue siendo validación propia.
CI del merge 39077241478 también success, mismo resultado completo.
Evidencia detallada: INTEGRATION_VALIDATION.md. Inicio 54 commits; cierre 57, faltan 444.

## Historial: Git y granularidad de implementación

Inicio: 4d99685, 22 commits, árbol limpio. Los contratos/catálogos del primer bloque
se conservaron al reanudar. Conteo antes del cierre:53; con este cierre documental,
54 totales y32 creados en la fase, sin squash. Restan447 para superar500 (501).
Cada cambio corresponde a contrato, catálogo, DTO, validación, servicio o tests real.
Rama publicada periódicamente. Confirmar números finales con git rev-list --count HEAD.

## Referencia de esquema

[tools/database-ref.json](../tools/database-ref.json) fija exactamente:
232c43130c0fb3eddd32e1dd3707368ba0d87d4c de M1nzutt/cognova-database.
Startup/readiness solo aceptan 0003_onboarding_questionnaire; rechazan0002,
revisiones desconocidas, ausencia y múltiples heads. No ejecutan migraciones.
No se diseñó/copió0003 ni se modificaron0001/0002.

ORM: User académico nullable; AcademicGoalLegacy de solo lectura;
QuestionnaireResponseRecord con PK(user_id,revision), JSONB completo y timestamp.
Modelo/esquema externo comparados en PostgreSQL, incluidos constraints relevantes.

## Contratos y comportamiento

[ONBOARDING_CONTRACT](ONBOARDING_CONTRACT.md), [AUTH_CONTRACT](AUTH_CONTRACT.md),
[QUESTIONNAIRE](QUESTIONNAIRE.md) y [API_CONTRACT](API_CONTRACT.md) son la referencia.

- POST /api/v1/auth/register recibe solo name/email/password; límites30/50/8–12.
  Name trim, email normalizado/único case-insensitive, extra=forbid;201 autentica
  con la seguridad previa y onboarding incomplete. Campos académicos NULL.
- Login conserva credenciales antiguas, incluso passwords/email más largos;
  no se reducen Argon2id/JWT/refresh/CSRF/logout/revocación/rate limiting/headers.
- UserResponse (register/login/me y PUT académico) incluye datos académicos nullable,
  onboarding explícito y legacy_academic_goal opcional. No objetivo vigente en User.
- PUT /api/v1/onboarding/academic-profile guarda degree_program trim/no vacío y
  semester entero positivo int32. No edita identidad ni objetivo histórico.
- GET /api/v1/questionnaire/catalog entrega catálogo1 con textos/IDs exactos.
- POST /api/v1/questionnaire crea inicial1; repetición409.
- GET /api/v1/questionnaire devuelve vigente o404 sin inicial.
- PUT /api/v1/questionnaire requiere expected_revision y agrega snapshot completo;
  revisión desactualizada409; sin inicial404. Lock User antes de consultar head.
- GET /api/v1/questionnaire/history pagina descendente, limit1..100 y cursor
  before_revision exclusivo; conserva baseline y todas las revisiones posteriores.
- Diez preguntas obligatorias, IDs/cardinalidades exactas, sin duplicados; Otro
  requiere trim1..50 y solo se admite en q1/q6/q7 cuando esté seleccionado.
- Codec traduce DTO choices/other_text a strings/arrays JSONB, prefijo reservado
  other:<texto>, reversible; nunca UPDATE/DELETE de la percepción inicial.
- OnboardingService concentra completitud: perfil válido + inicial completa válida.
  Cualquiera puede llenarse primero; auth/restore/logout funcionan incomplete.
- get_onboarded_user queda disponible para futuros módulos académicos (403
  ONBOARDING_REQUIRED). No se implementaron materias, actividades, sesiones ni IA.

Usuarios migrados: archivo legacy conserva incluso blancos/Unicode literalmente;
no fabrica cuestionarios ni cambia academic_goal original. Sesiones preexistentes
siguen válidas. Identidad legacy fuera de los checks físicos30/50 sigue pudiendo
iniciar sesión/leer; rehash se difiere y edición académica devuelve409
LEGACY_PROFILE_REMEDIATION_REQUIRED hasta remediación explícita, sin truncar datos.

## Pruebas y controles

CI de código completo: [38349589618](https://github.com/M1nzutt/cognova-backend/actions/runs/38349589618),
commit9f7b31c; CI final con documentación sincronizada:
[38349751140](https://github.com/M1nzutt/cognova-backend/actions/runs/38349751140),
commite18b4de. Ambos success.

- **226 passed, 0 skipped**,84 casos de integración PostgreSQL17.
- **1 passed adicional**: wheel instalado, imports físicos y launcher TCP real,
  sin Alembic ni cognova_database en runtime.
- Ruff check y format correctos; local109 archivos conformes.
- Mypy sin problemas en76 archivos source.
- Build sdist/wheel correcto; módulos catálogo incluidos.
- pip-audit: sin vulnerabilidades conocidas; gitleaks aprobado.
- OpenAPI prueba campos exactos, límites, seguridad, endpoints/status DTOs.
- Registro bordes, auth completa, restore incomplete, ambos órdenes onboarding,
  ownership, catálogo, validaciones, inicial/versionado/paginación/concurrencia.
- Upgrade desde0002 para usuarios/sesiones reales de prueba; objetivos preservados,
  login largo legacy, constraints de identidad y snapshots inmutables.
- Localmente77 tests puros de schemas/catálogo/codec aprobados; PostgreSQL/stack
  dependiente de DLL se certificó en CI Linux por restricciones previas de Windows.

Dos warnings no fatales visibles: deprecación httpx/Starlette TestClient y warning
SQLAlchemy/Alembic al reflejar dialect_options de checks NOT VALID. No se ocultan;
la comparación ORM pasa y pruebas directas demuestran enforcement de constraints.
No hay tests fallidos, omisiones de integración ni excepciones de seguridad aceptadas.

Último commit solo documentación/evidencia: no repite CI del mismo código validado.
Antes de cierre se revisaron diff/check, links y estado Git; no secretos versionados.

## Commits principales de la fase

fb9b002 contratos;3f02158..efc71c9 diez grupos de opciones;fe3c324 catálogo tipado;
8f01920/f18bbbf validadores y tests;66c9dfd codec;38bfa59 ORM;5c017ae pin/readiness;
e9c02da DTOs;59c3e87 versionado;6fb6c08 estado central; c38442d routers;
4dc4dd3 registro mínimo;57fcac3 onboarding tests;6ffa2be historial/concurrencia;
d4fd37b migración/legacy;8bb1ed4 límitesDB;9f7b31c OpenAPI;
4982f25/144ea8a/0541fd7/e18b4de documentación y principio IA oficial.
El hash del cierre figura en git log. No inflar historial ni squash posterior.

## Dependencias externas reales y siguiente paso

FRONTEND: consumir registro de3 campos y UserResponse.onboarding; usar next_step
para perfil/cuestionario/completo sin adivinar por strings. Leer catálogo1, enviar
las10 respuestas y Otro conforme DTO; guardar expected_revision para PUT, manejar
409/releer, presentar historial paginado. Mantener auth actual, proxy/origen/cookies
sin cambios y consultar /auth/me tras refresh/restauración. Ver contrato público.

DATABASE/OPERACIÓN: release requiere0003 aplicado y permisos de nuevas tablas/funciones.
Coordinar antes del merge/deploy; rama backend no aplica DDL. Identidades históricas
no conformes requieren remediación explícita si existen en producción. No cambiar
el SHA pedido por un commit documental ni reabrir handoff inicial.

La IA observa, relaciona, cuestiona y pregunta. El usuario interpreta y decide.
Mínimo5 sesiones válidas para patrones. No se implementa Gemini en esta fase.
La fase de código está terminada; siguiente paso es integración frontend y release
coordinado de este contrato, antes de desarrollar materias/otros módulos.
