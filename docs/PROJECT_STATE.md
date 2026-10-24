# Cognova — Estado backend

## Actividades en implementación — 2026-10-23

Inicio limpio main da2845d, 70 commits. Rama feat/activities-0005.
Contrato definido en ACTIVITIES_CONTRACT; DB fijará SHA 604e296e2670d154ba7e18d7afa3f010e66dd42d.
Lectura de reglas/contratos y revisión Git completadas. Pin/ORM/readiness implementados: 11 tests unitarios y 3 PostgreSQL aprobados
(compatibilidad ORM sin drift, startup read-only, readiness). DTOs, filtros y matriz de transiciones validados con 56 pruebas unitarias nuevas.
Servicio transaccional implementado, 6 pruebas adicionales de retry/errores pasan.
CRUD/historia/OpenAPI aprobados: 6 escenarios PostgreSQL y 1 OpenAPI nuevos,
incluidos ownership, precondiciones concurrentes y DELETE con/sin historial.
Suite completa y controles de runtime aún pendientes; sin cambios de auth ni acciones productivas.


## Backend Materias cerrado — 2026-10-20

Smoke DELETE final aprobado el 2026-10-20, 15:41:48–15:43:12Z, después del permiso
DELETE concedido por Database. SHA productivo reconfirmado Live:
430c64a3c299f82853f7947498f663f1cded590c; sin redeploy ni cambios funcionales.
Runtime cognova_runtime, TLS y 0004_subjects; DELETE permitido, TRUNCATE y CREATE
public denegados. Backend no modificó schema ni grants.

Materia sintética 8: creación 201, DELETE confirm=true 204 sin cuerpo, GET posterior
404 y segundo DELETE 404; ausente del listado y de PostgreSQL (count=0, READ ONLY).
Materia ajena 1 del usuario sintético 5 intacta en todas sus columnas; ajena e
inexistente devuelven el mismo 404. Auth/CSRF/cookies/no-store correctos:
sin Bearer 401, sin confirmación 422, refresh/logout sin CSRF 403, con CSRF 200/204,
access revocado 401. Readiness antes/después 200. Cuenta sintética 7 y cuestionario
inicial retenidos; sesión cerrada. Solo se borró la materia creada para esta prueba.

**Backend Materias queda cerrado; Frontend puede continuar con el contrato completo,
incluido DELETE.** La validación de navegador/proxy sigue siendo responsabilidad
Frontend. El resto del módulo ya estaba aprobado por el smoke anterior.
Evidencias locales revisadas: .local/subjects-delete-smoke.json y
.local/subjects-delete-runtime.json; detalle permanente en INTEGRATION_VALIDATION.
No se repitió la suite ni el smoke CRUD completo para este cierre documental.

Inicio limpio 5aa90c1, 69 commits. Un solo commit documental deja 70 totales,
sin squash, con [skip ci] [skip render]. Únicamente PROJECT_STATE, DEPLOYMENT e
INTEGRATION_VALIDATION actualizados. Los bloqueos siguientes son historial resuelto.

## Materias desplegado; cierre bloqueado por DELETE — 2026-10-20

Retomado desde main limpio en 430c64a (68 commits). El merge --no-ff y push ya
se habían completado el 2026-10-19; no se repitieron. feat/subjects-0004 permanece
en d00ce49, íntegra como segundo padre del merge. Render confirma Live del SHA
430c64a3c299f82853f7947498f663f1cded590c, deploy dep-dbb5fujm8hqs73eumf8g,
en el servicio existente srv-db2j6nqj9qps73crqa0g. Readiness HTTP 200 antes y después
del smoke. Conexión efectiva cognova_runtime, TLS y exactamente 0004_subjects.

CI de preparación 39296759454 y del merge 39297303193 reconfirmados success:
281 tests, 0 omitidos, 111 PostgreSQL; 1 adicional de wheel/launcher HTTP.
Ruff, mypy (86 archivos), build, pip-audit y gitleaks aprobados. Post-smoke local:
Ruff/formato (125 archivos) y mypy correctos. Dos warnings conocidos no fatales
(Starlette/httpx y reflexión de checks); no cambios en app runtime en este release.

Smoke real 2026-10-20 15:25:26–15:26:33Z: catálogo, crear/listar/detalle/editar,
archivar/reactivar, cinco activas, duplicados y aislamiento aprobados. Auth,
onboarding, cookies, CSRF, refresh, revocación y no-store también aprobados.
404 indistinguible para ajena/inexistente; 409 para duplicados/capacidad.
DELETE confirmado devuelve 503 SERVICE_UNAVAILABLE, sin detalles nativos y sin
borrar la materia. EXPLAIN DELETE bajo la credencial runtime efectiva devuelve
42501; SELECT/INSERT/UPDATE/secuencia sí están permitidos. No se cambiaron grants.

**Materias no se cierra. DEPENDENCY DATABASE: exclusivamente permiso DELETE en
public.subjects para cognova_runtime**, según SUBJECTS_CONTRACT. Sin DDL ni grants
globales. Después del ajuste por Database, Backend debe repetir DELETE autorizado
204, segunda eliminación/lectura 404 y confirmar permisos/ownership/no-store.
Frontend puede comenzar integración del contrato y los flujos validados; no dar
por completo el CRUD productivo ni presentar DELETE como operativo antes de eso.

Evidencia: [smoke](evidence/subjects-smoke-2026-10-20.json),
[runtime posterior](evidence/subjects-runtime-2026-10-20.json) y
[validación](INTEGRATION_VALIDATION.md). Usuarios sintéticos 5/6 retenidos, siete
materias archivadas (6/1), dos snapshots por usuario y cuatro sesiones revocadas;
cero sesiones sintéticas activas. No se borra su historia ni se toca otro usuario.
No frontend, actividades, schema ni configuración Render modificados.

Esta continuación añade un commit de evidencia/documentación: 69 totales.
Release completo: d00ce49 preparación, 430c64a merge y este registro (3 nuevos desde
los 66 iniciales), sin squash. Commit documental con [skip ci] [skip render]
para conservar el SHA productivo validado. Los apartados siguientes son historial.

## Release Materias en preparación — 2026-10-19

Inicio limpio en feat/subjects-0004, 06f6c4b1c94ddf6da4c78b518b2f7ccc0d2ad63c,
66 commits. Usuario autoriza merge sin squash y deploy al servicio Render
srv-db2j6nqj9qps73crqa0g existente, rama main, autoDeploy=yes. Live previo 9309eff.
Preflight con la credencial runtime efectiva de Render: cognova_runtime, TLS,
exactamente 0004_subjects; SELECT/INSERT/UPDATE subjects y USAGE/SELECT secuencia.
DELETE/TRUNCATE denegados, CREATE public denegado; EXPLAIN DELETE da 42501.
No se cambian schema, grants, secretos, auth ni recursos Render.

Preparado scripts/smoke_subjects.py: crea dos usuarios sintéticos, valida onboarding,
catálogo/crear/listar/detalle/editar/archivar/reactivar, capacidad, duplicados,
ownership 404, DELETE explícito, no-store, CSRF/cookies, refresh y revocación.
Retiene usuarios/cuestionarios; archiva las materias sintéticas y cierra sesiones.
--expected-delete=503 registra el bloqueo por separado, nunca cierre completo.
Ensayo nuevo contra API/PostgreSQL desechable: 1 passed. Ruff y mypy correctos.
Suite previa 280 casos en ejecución; CI de la implementación c62cde0 verificado
success (39196997553). Código app runtime idéntico al SHA final comunicado.
Siguiente: validar CI de preparación, merge --no-ff, deploy y smoke real.


## Materias — entrega cerrada 2026-10-19

Rama feat/subjects-0004. Inicio limpio dec1f73 (57 commits); nueve commits de
Materias dejan 66 totales, sin squash. Esta continuación aporta dos commits
documentales: sincronización pendiente y evidencia final. No cambia funcionalidad.

Database fijado a c3394c38c55a8cd466d10f02fe7c80d7c1e1980f, revisión 0004_subjects.
Contrato público: [SUBJECTS_CONTRACT](SUBJECTS_CONTRACT.md).
ORM, schemas, servicio y rutas separados. Auth, frontend y Database sin cambios.

CI final [39196997553](https://github.com/M1nzutt/cognova-backend/actions/runs/39196997553):
**completed / success**, sobre c62cde02bbeda0265e7723b604ac5f8abe099c72.
280 pruebas aprobadas, 0 omitidas, 110 casos PostgreSQL; además 1 prueba del wheel
instalado y launcher HTTP real. Runtime sin Alembic/cognova_database comprobado.
Ruff lint/formato, mypy (86 archivos), build sdist/wheel, pip-audit y gitleaks pasan.
Los cierres posteriores solo documentales conservan ese código validado; se
revisaron enlaces, diff y ausencia de cambios runtime antes de publicar.

La suite local también pasó 280 pruebas; JUnit .local/subjects-results.xml validado.
PostgreSQL desechable detenido y cero esquemas test_* residuales. Dos warnings
existentes no fatales: Starlette/httpx y reflexión SQLAlchemy/Alembic de checks
NOT VALID. Sin fallos ni omisiones aceptados.

Nombre 1–20, NFC/strip y unicidad Unicode casefold por usuario, incluidas archivadas;
índice DB lower(name) conservado. Catálogo de diez bases y shades 100/200/300/400/500.
Máximo cinco activas mediante posiciones DB; archivo/reactivación conservan identidad.
Mutaciones READ COMMITTED con lock de User y máximo tres intentos completos ante
conflictos recuperables. El caso É/é en collation C quedó corregido y probado.

Bearer y onboarding completo obligatorios; ownership en toda consulta, ajena e
inexistente devuelven el mismo 404. DELETE requiere confirm=true y respeta FK:
409 si hay dependencias. Los 26 casos PostgreSQL de Materias cubren concurrencia,
rollback/reintentos reales, Unicode, paginación, permisos API, OpenAPI y upgrade
desde 0003 conservando usuarios, sesiones, buckets y cuestionarios.

**Siguiente dependencia real: Database/operación 0004 en producción**, con respaldo,
migrador y grants SELECT/INSERT/UPDATE/DELETE de subjects más USAGE/SELECT de
subjects_id_seq para runtime. Backend rechaza 0003; coordinar migración y release.
No se aplicó DDL productivo, no se cambiaron grants, no hubo merge ni despliegue.
Frontend puede integrar el contrato; consumo productivo espera ese corte.

Commits: bee90dd contrato; 50b06ea pin/ORM; 540256c DTOs; 09a5cf5 servicio;
34eed65 rutas/OpenAPI; 4162c53 Unicode/transacciones; c62cde0 integración;
3c4e270 sincronización documental; el noveno commit incorpora esta evidencia final.
Las referencias y cifras siguientes pertenecen al historial de onboarding.

## Historial de onboarding

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
