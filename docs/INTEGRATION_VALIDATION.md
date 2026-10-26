# Validación de integración productiva

## Calendario v1 — validación local/CI 2026-10-25, sin deploy

GET /api/v1/calendar: [contrato](CALENDAR_CONTRACT.md), código bb75d41.
25 pruebas nuevas (20 unitarias/OpenAPI/errores, 5 PostgreSQL). Verifican rango
semiabierto, offsets equivalentes, ventanas inválidas y límite 366 días, cursor
pareado, orden cronológico con empates, paginación sin duplicados con datos estables,
filtros AND, materias archivadas, actividad ajena oculta, onboarding obligatorio,
401/403/422/503 sanitizado y no-store. Mutaciones de Calendario rechazadas con405.
Cambiar deadline desde Actividades mueve el elemento sin duplicarlo; fecha original
e historial postponed/rescheduled conservados. DELETE del recurso original se refleja.
Snapshots activities/history/subjects antes/después de consultas coinciden.

Suite completa: 386 passed, 130 PostgreSQL, cero skipped/fallos. Ruff/formato, mypy,
build y auditoría aprobados. CI [40255644217](https://github.com/M1nzutt/cognova-backend/actions/runs/40255644217)
success; incluye instalación runtime sin tooling DB y launcher real del wheel.
Sin nueva prueba productiva, credenciales/grants de producción ni acceso a otros repos.
Frontend puede integrar; despliegue y smoke Calendario pertenecen al release siguiente.

## Actividades — smoke productivo final aprobado (2026-10-24)

SHA fe5989b86d93d10e724cbf28de4f9d64048bb711, deploy dep-dbeh7u15efls73b1uqag Live.
Smoke HTTP real 20:25:51–20:26:12Z, Origin frontend existente. Backend exige 0005;
PostgreSQL real confirma 0005_activities/TLS/cognova_runtime. Ningún grant/schema
cambiado desde Backend. No se afirma validación visual ni proxy de navegador.

| Control | Resultado |
| --- | --- |
| Readiness antes/después, OpenAPI | 200; rutas Actividades presentes |
| Crear / listar / detalle / editar | 201 / 200 / 200 / 200 |
| Filtros materia, estado, prioridad, deadline exacto/rango inclusivo/combinado | 200, inclusión/exclusión correctas |
| Pending→in_progress→completed→pending→cancelled | 200; estado/deadline independientes |
| Estado esperado obsoleto / terminal sin reapertura | 409 ACTIVITY_STATE_CONFLICT / ACTIVITY_TRANSITION_CONFLICT |
| Deadline adelante / atrás | 200; postponed / rescheduled |
| Instante equivalente con otra zona | 200, sin evento nuevo |
| Dos PATCH concurrentes con expected_revision=2 | uno 200, otro 409 ACTIVITY_DEADLINE_CONFLICT; revisión 3 |
| Historial / fecha inicial | tres eventos encadenados; original 2030-01-01T12:00:00Z intacto |
| DELETE con historia / materia con actividad | 409 ACTIVITY_HAS_DEPENDENCIES / SUBJECT_HAS_DEPENDENCIES; conservadas |
| DELETE sin confirmación / sin historia confirmado | 422 / 204 sin cuerpo |
| GET después / segundo DELETE / listado | 404 / 404 / ausente |
| Ajena/inexistente, todas las rutas y materia ajena | 404 indistinguible; listado ajeno vacío |
| Título 51, duración 9, fecha sin zona, user_id extra, rango invertido | 422, error genérico |
| Sin Bearer / onboarding pendiente | 401 / 403 |
| Refresh/logout sin CSRF / válidos | 403 / 200 y 204; refresh rotado, access revocado 401 |
| Cookies / caché | Secure, paths, host-only, HttpOnly y SameSite correctos; no-store en todas las respuestas verificadas |
| Archivado de materia | actividad conservada, accesible |

Primer intento 20:20:49–20:21:08Z sobre 2221e85 detectó 503 al borrar actividad con
historia. Diagnóstico con credencial runtime y transacción revertida: SQLSTATE 23001,
constraint fk_deadline_events_activity, fila intacta. PostgreSQL 18.6 productivo
usa 23001 donde PostgreSQL 17 local devolvía 23503. Corrección mínima en servicios
traduce ambos a 409 al borrar; sin exponer errores nativos. Se añadió regresión para
ambos SQLSTATE y DELETE con historia bajo rol restringido. El 503 por permiso DB
faltante sigue probado mediante fallo controlado local; no se revocaron grants
productivos para inducirlo. El segundo smoke aprobado certifica la corrección real.

Verificación READ ONLY 20:26:43Z: actividad 2 usuario 18 cancelada, revisión 3, fecha
original intacta; eventos postponed/rescheduled/postponed encadenados. Actividad 3
borrada count=0. Materias 30/31 archivadas. Usuarios 18/19 y sus cuestionarios/historia
retenidos deliberadamente. Primer intento conserva usuarios 16/17, materias 28/29
activas y actividad 1 con historial; no se pudo completar archivado al abortar el
smoke, y no se hizo limpieza SQL ni se borró historia. Las cuatro sesiones sintéticas
están revocadas; cero activas. No se modificaron filas de otros usuarios.

Pruebas finales: 361 pruebas aprobadas, 125 PostgreSQL, cero fallos y cero omitidas. Ruff check/formato 147 archivos y mypy 101
correctos; build sdist/wheel aprobado. CI merge 40129132661 success; CI final:
[40129775095](https://github.com/M1nzutt/cognova-backend/actions/runs/40129775095) success sobre 5535585; corrección [40129632727](https://github.com/M1nzutt/cognova-backend/actions/runs/40129632727) success. Warnings conocidos no fatales: Starlette/httpx y reflexión de checks.

Evidencia sin secretos: [smoke final](evidence/activities-smoke-2026-10-24.json),
[runtime final](evidence/activities-runtime-2026-10-24.json),
[primer intento](evidence/activities-first-attempt-2026-10-24.json) y
[diagnóstico RESTRICT](evidence/activities-restrict-2026-10-24.json),
[despliegue](evidence/activities-deploy-2026-10-24.json) y
[suite final](evidence/activities-tests-2026-10-24.json).
Backend Actividades validado en producción; Frontend puede continuar con el contrato.

Los apartados siguientes son históricos: sus revisiones y bloqueos corresponden
a cada fecha, no a pendientes del release 0005 cerrado.

## Histórico — Actividades — evidencia local y CI, sin smoke productivo (2026-10-23)

Código 3f0c0cd992119aea985c1a23d6e271ea8b94faf2; DB
604e296e2670d154ba7e18d7afa3f010e66dd42d / 0005_activities.
358 tests locales, 124 PostgreSQL17.11, sin skips; JUnit validado por
scripts/check_test_results.py. CI40050090141 completed/success.

- POST201; GET/list/PUT/PATCH200; DELETE confirmado sin historia204 y posterior404.
- Ajena/inexistente:404 idéntico en cada ruta; asignar materia ajena/inexistente404.
- Filtros combinados, cursor, rango inclusivo y mismo instante con offset distinto.
- deadline mayor/menor registra postponed/rescheduled; fecha inicial inmutable.
- Mismo instante no añade evento; PUT también registra historia. Estado independiente.
- Terminal a otro estado sin reapertura409; precondiciones desactualizadas409.
- Dos cambios concurrentes con misma revisión: uno confirma y otro409; un solo evento.
- Historia existente/FK futura bloquean DELETE409; actividad/materia preservadas.
- Carrera crear actividad/borrar materia serializada; sin huérfanos.
- Error al escribir historia revierte actividad; abortos40001/40P01 reintentan completos.
- Upgrade0004 preserva usuarios/sesiones/cuestionarios/materias; ORM sin drift.
- Rol temporal local: DML actividades funciona, trigger escribe historia sin grants
  directos; DDL/escritura historia/revisión/EXECUTE de trigger denegados42501.
  Revocar DELETE local produce HTTP503 genérico y conserva fila. Sin cambios de grants
  productivos. El rol de prueba se elimina al terminar.
- Bearer/onboarding/CSRF/no-store correctos; regresión completa de auth/Materias pasa.
- OpenAPI documenta requests, filtros, security, errores y DELETE204 sin cuerpo.
- Wheel aislado sin tooling de migración: launcher/readiness/Actividades401 aprobados.

Ruff, mypy, pip check, build y auditoría correctos. Pin de opentelemetry-api corregido
1.45.0→1.45.1 por CVE-2026-114603. No se hizo smoke en Render; requiere release DB0005
más permisos y deploy Backend coordinados. Frontend puede desarrollar en paralelo.


## Histórico — DELETE final aprobado y Backend Materias cerrado — 2026-10-20

Smoke limitado posterior al grant de Database, ejecutado 15:41:48–15:43:12Z.
SHA Live reconfirmado: 430c64a3c299f82853f7947498f663f1cded590c, deploy
 dep-dbb5fujm8hqs73eumf8g, servicio srv-db2j6nqj9qps73crqa0g. Sin redeploy.
Conexión efectiva cognova_runtime/TLS/0004_subjects: DELETE subjects permitido;
TRUNCATE y CREATE public siguen denegados. No se otorgaron permisos desde Backend.

| Control | Resultado real |
| --- | --- |
| Crear materia sintética propia id=8 | 201 |
| DELETE confirm=true | 204, cuerpo vacío |
| GET posterior / segundo DELETE | 404 / 404 SUBJECT_NOT_FOUND |
| Listado posterior | 200, materia ausente |
| PostgreSQL READ ONLY | count=0 para la materia borrada |
| DELETE ajena id=1 / inexistente | 404 SUBJECT_NOT_FOUND idéntico |
| Materia ajena del usuario sintético 5 | Todas las columnas preservadas |
| DELETE sin Bearer / sin confirmación | 401 / 422 |
| Refresh sin CSRF / válido | 403 / 200, rotación comprobada |
| Logout sin CSRF / válido / access posterior | 403 / 204 / 401 |
| Cookies | Secure, HttpOnly solo refresh, paths/host-only/SameSite=Lax correctos |
| Cache-Control | no-store en todas las respuestas API comprobadas, incluidos 204 y errores |
| Readiness antes / después | 200 / 200 |

Cuenta sintética 7 y cuestionario inicial retenidos; sesión cerrada. Solo se eliminó
la materia creada para este smoke. No se modificó código ni se repitió el CRUD
completo: sus controles ya constan en el smoke anterior. Evidencias locales
revisadas: .local/subjects-delete-smoke.json (status=passed) y
.local/subjects-delete-runtime.json. No se imprimieron credenciales.

**Dependencia DELETE resuelta; Backend Materias cerrado. Frontend puede continuar
con todo el contrato.** Los resultados 503/42501 de las secciones siguientes
son anteriores al grant y se conservan como trazabilidad. CI previo del mismo SHA:
281 pruebas sin omisiones, 111 PostgreSQL y launcher adicional; no se afirma una
nueva ejecución de esa suite para este cambio exclusivamente documental.

## Histórico — Materias — validación productiva 2026-10-20

Main integra feat/subjects-0004 mediante merge --no-ff
430c64a3c299f82853f7947498f663f1cded590c; segundo padre d00ce49, sin squash.
Render srv-db2j6nqj9qps73crqa0g confirma ese SHA Live, deploy
 dep-dbb5fujm8hqs73eumf8g. El merge/push se completaron antes de reanudar;
no se repitieron ni se crearon recursos. Endpoint:
https://cognova-backend-lpsi.onrender.com, Origin https://cognova-frontend.netlify.app.

[CI preparación 39296759454](https://github.com/M1nzutt/cognova-backend/actions/runs/39296759454)
y [CI merge 39297303193](https://github.com/M1nzutt/cognova-backend/actions/runs/39297303193):
completed/success reconfirmados. 281 passed, 0 skipped, 111 PostgreSQL; 1 prueba
adicional de wheel y launcher HTTP. Ruff, formato, mypy, build, audit y gitleaks
pasan. Local previo: 280 tests más 1 ensayo nuevo; post-smoke Ruff/formato/mypy
pasan. Los dos warnings existentes no fatales se mantienen documentados.

Smoke real ejecutado con scripts/smoke_subjects.py, --expected-delete 503:
2026-10-20T15:25:26Z a 15:26:33Z. Evidencia sin credenciales:
[HTTP](evidence/subjects-smoke-2026-10-20.json) y
[runtime READ ONLY posterior](evidence/subjects-runtime-2026-10-20.json).

| Control | Resultado real |
| --- | --- |
| Health/readiness antes y readiness después | 200; revisión exacta 0004_subjects |
| Catálogo sin Bearer / onboarding incompleto | 401 / 403 ONBOARDING_REQUIRED |
| Catálogo autenticado | 200; versión 1, diez bases, cinco shades |
| Crear / listar / detalle / editar | 201 / 200 / 200 / 200 |
| Archivar / reactivar | 200 / 200; identidad conservada |
| Crear sexta activa | 409 SUBJECT_ACTIVE_LIMIT |
| Crear archivada con cinco activas | 201, no consume cupo |
| Reactivar sin cupo / liberar y reutilizar slot | 409 SUBJECT_REACTIVATION_LIMIT / 200 |
| Duplicado y nombre reservado por archivada | 409 SUBJECT_NAME_CONFLICT |
| Mismo nombre en otro usuario | 201 |
| Ajena GET/PUT/archive/reactivate/DELETE | 404 SUBJECT_NOT_FOUND, igual a inexistente |
| Listados entre usuarios | Aislados |
| DELETE sin confirmación | 422 VALIDATION_ERROR |
| DELETE propio confirm=true | 503 SERVICE_UNAVAILABLE; fila íntegra al releer |
| Cookies y CSRF/refresh | Atributos correctos; sin CSRF 403, válido 200 y rotación |
| Revocación / logout / access revocado | 204 / 204 / 401 |
| Cache-Control | no-store en todas las respuestas API comprobadas, incluidos errores |

El cuerpo DELETE es exactamente error.code=SERVICE_UNAVAILABLE y message=
"Servicio temporalmente no disponible."; no expone SQL ni datos internos.
La credencial DATABASE_URL real de Render conecta como cognova_runtime vía TLS:
SELECT/INSERT/UPDATE subjects y USAGE/SELECT subjects_id_seq permitidos;
DELETE/TRUNCATE denegados, sin CREATE public. EXPLAIN DELETE sin ejecución devuelve
42501 antes y después del smoke. El resto del ciclo funciona y el error SQL de
permisos se traduce al 503 global esperado, sin borrar la materia. No se otorgan
permisos ni se modifica schema, auth o configuración desde Backend.

Verificación posterior 15:27:07Z: usuarios sintéticos 5/6 conservan revisiones [1,2]
cada uno; materias 6/1, todas archived; sesiones 2/2, ninguna sin revocar.
El smoke solo retuvo y archivó sus propios registros; no eliminó historia.

**Bloqueo pendiente único: DELETE en Database.** Solicitar permiso específico
sobre public.subjects para cognova_runtime; después repetir por API 204, segundo
DELETE/GET 404, ownership y no-store. No cerrar Materias hasta entonces.
Frontend puede comenzar los flujos validados; eliminación productiva pendiente.
Este smoke HTTP no sustituye la validación de navegador/proxy del frontend.

## Historial: onboarding — 2026-10-17


Fecha: 2026-10-17. Rama main. Onboarding desplegado y smoke aprobado.

## Histórico — Runtime y permisos

Servicio srv-db2j6nqj9qps73crqa0g, base existente en 0003_onboarding_questionnaire.
Se inspeccionó DATABASE_URL efectiva en Render sin imprimirla: antes usaba
cognova_user propietario. Se creó cognova_runtime LOGIN NOINHERIT NOSUPERUSER
NOCREATEDB NOCREATEROLE NOREPLICATION y se actualizó únicamente DATABASE_URL.
Contraseña aleatoria generada en memoria, verificador SCRAM en PostgreSQL y
secreto almacenado en Render; nada versionado. Migrador/ownership sin cambios.

Permisos comprobados conectando con esa credencial al mismo recurso:

| Objeto | Permisos runtime |
| --- | --- |
| users, auth_sessions | SELECT, INSERT, UPDATE |
| rate_limit_buckets | SELECT, INSERT, UPDATE, DELETE |
| alembic_version, user_academic_goal_legacy | SELECT |
| questionnaire_responses | SELECT, INSERT |
| users_id_seq | USAGE, SELECT |
| Tres funciones de cuestionario/historia | EXECUTE |
| public | USAGE, sin CREATE |

Sin ownership ni UPDATE/DELETE de historia ni escritura de alembic_version.
Permisos de futuras tablas deben otorgarse deliberadamente, sin grants globales.
La comprobación local usó el endpoint externo del mismo recurso; Render conserva
el interno. El nuevo deploy cargó la conexión y pasó readiness y smoke real.

## Histórico — Git, CI y deploy

- 40ed5baf8001d6a75c9a7010b3a67ff795900b14: smoke y preparación operativa.
- [CI previo 39077069939](https://github.com/M1nzutt/cognova-backend/actions/runs/39077069939): success.
  226 passed, 0 skipped; PostgreSQL real y control JUnit. Prueba adicional de wheel/
  launcher: 1 passed. Ruff/formato, mypy (76 archivos), build, pip-audit y gitleaks pasan.
- Local: 77 tests puros passed; Ruff y formato (109 archivos) correctos.
- Merge --no-ff, sin squash: 9309effdd1b71acc3fe5e24bc8c19b70c3d8c0c8.
  Árbol idéntico a la rama validada; historial de onboarding íntegro.
- Render deploy dep-db9vrie7bikc73e676q0: Live, mismo SHA del merge.
- [CI del merge 39077241478](https://github.com/M1nzutt/cognova-backend/actions/runs/39077241478): success;
  mismos 226 tests, launcher adicional y controles completos aprobados.

## Histórico — Smoke real

Ejecutado scripts/smoke_auth.py contra https://cognova-backend-lpsi.onrender.com,
con Origin https://cognova-frontend.netlify.app. Credenciales/tokens/cookies solo
se mantuvieron en memoria; no se imprimieron cuerpos sensibles.

| Control | Resultado |
| --- | --- |
| GET /api/v1/health, /api/v1/ready | 200 / 200 |
| GET /openapi.json | 200; rutas onboarding presentes |
| GET /api/v1/auth/me sin sesión | 401 |
| Register mínimo / login / me | 201 / 200 / 200 |
| PUT academic-profile / GET catálogo | 200 / 200 |
| POST inicial / GET actual | 201 / 200, revisión 1 idéntica |
| PUT expected_revision=1 | 200, revisión 2 |
| Repetir expected_revision=1 | 409 |
| GET history | 200, revisiones [2,1], inicial intacta |
| GET me tras onboarding | 200, status complete |
| Refresh sin CSRF / válido | 403 / 200, refresh rotado |
| Me después de refresh / sesiones | 200 / 200 |
| Revocar otra sesión / access revocado | 204 / 401 |
| Logout / access después de logout | 204 / 401 |

Cookies: Secure ambas, refresh HttpOnly con Path=/api/v1/auth; CSRF no HttpOnly
con Path=/; ambas host-only y SameSite=Lax. Cache-Control no-store comprobado en
todas las respuestas API del smoke, incluidas errores y 204.
Verificación PostgreSQL READ ONLY adicional: 1 usuario sintético reciente,
2 sesiones, 0 sin revocar, 2 respuestas con revisiones [1,2]. La cuenta y su
historial permanecen deliberadamente; no se borran datos ni se fabrica limpieza.

## Histórico — Alcance del cierre

Backend listo para frontend compatible con el contrato. No se desplegó ni modificó
frontend/database. E2E de navegador y proxy Netlify siguen a cargo del frontend;
este smoke HTTP no los sustituye. No volver a aplicar 0003 ni desplegar el backend
antiguo que exige 0002. HealthCheckPath de Render permanece vacío; no se cambió
configuración ajena al rol runtime. Inicio 54 commits; cierre 57, faltan 444 a 501.
