# Despliegue existente y transición de base de datos
## Release autorizado Materias — 2026-10-19, preparación

Database ya está en 0004. Verificado con la DATABASE_URL efectiva de Render,
sin imprimirla: cognova_runtime y TLS; falta exclusivamente DELETE en subjects.
La autorización actual permite merge/deploy y smoke aun con ese permiso pendiente;
no concede permiso para ajustar grants desde Backend ni para cerrar Materias.
Conservar servicio srv-db2j6nqj9qps73crqa0g, main y autoDeploy=yes. No Blueprint.

Smoke autorizado después de Live/readiness:
`python -m scripts.smoke_subjects https://cognova-backend-lpsi.onrender.com
--frontend-origin https://cognova-frontend.netlify.app --expected-delete 503
--evidence .local/subjects-live-smoke.json` (una línea).
Crea dos cuentas sintéticas y conserva su historia; solo archiva sus materias,
revoca sesiones y no ejecuta SQL mutante ni grants. Guarda evidencias sin secretos.
Ante DELETE 503, verificar 42501 con la credencial runtime y documentar Database
como dependencia del permiso; no confundir con 409 por FK o con cierre del módulo.
Después del grant operado por Database, repetir DELETE esperando 204 y segundo
intento 404 antes de cerrar CRUD. Nunca saltar readiness ni revertir a 0003.


## Materias — pendiente de rollout

La rama feat/subjects-0004 exige exactamente 0004_subjects. No mergear/desplegar
sobre producción 0003. Database/operación deben respaldar y aplicar 0004 con el
migrador, revisar SELECT/INSERT/UPDATE/DELETE de subjects y USAGE/SELECT de
subjects_id_seq para cognova_runtime, y coordinar la ventana de cambio de readiness.
No se modifican grants ni producción desde esta tarea. Después desplegar Backend
y probar CRUD/ownership/archivo/reactivación con el rol runtime. Frontend puede
integrar SUBJECTS_CONTRACT.md; consumo productivo queda pendiente de ese release.

## Release operativo autorizado — 2026-10-17

Base productiva en 0003, verificada usando la conexión efectiva de Render.
Rol previo cognova_user propietario; nuevo runtime cognova_runtime con permisos
mínimos descritos en PROJECT_STATE. DATABASE_URL actualizada en el mismo servicio,
sin cambiar base, JWT, cookies, CORS, build/start ni crear recursos Render.
La conexión externa del mismo recurso se usó para comprobar el rol desde la
estación; el servicio conserva su endpoint interno. No exponer ninguna URL.
Integrado sin squash y desplegado SHA 9309effdd1b71acc3fe5e24bc8c19b70c3d8c0c8.
Deploy dep-db9vrie7bikc73e676q0 confirmado Live. Smoke ejecutado sobre Render
con Origin https://cognova-frontend.netlify.app.
Este smoke sí crea una cuenta sintética con dos snapshots y revoca sus sesiones;
la autorización actual sustituye la prohibición histórica de smoke documental.
Health/readiness/OpenAPI 200 y me sin sesión 401; flujo completo y seguridad pasan.
Evidencia final en INTEGRATION_VALIDATION.md. Frontend compatible puede desplegarse.
La rama sigue en autoDeploy=yes; commit final solo documental usa [skip render]
para conservar el SHA probado. No se cambió healthCheckPath (sigue vacío).
No rollback a 3e3ed95: ese launcher exige 0002 y ya no es compatible con la base.

## Historial: release de onboarding (rama, sin desplegar)

El código de feat/onboarding-questionnaire requiere exactamente 0003_onboarding_questionnaire
y database232c43130c0fb3eddd32e1dd3707368ba0d87d4c. No merge/deploy automático sobre0002.
Database/operación coordinan migración y permisos, luego el release compatible.
Las observaciones de producción descritas abajo pertenecen al despliegue anterior;
esta fase no toca Render, Netlify ni ejecuta DDL productivo.

## Historial: estado conocido del despliegue anterior

Servicio y configuración inspeccionados en Render el 2026-10-11:

- Backend: https://cognova-backend-lpsi.onrender.com (`lpsi` con letra ele).
- PostgreSQL: Render Postgres (identificador, revisión aplicada y grants no
  inspeccionados en esta fase).
- Frontend: https://cognova-frontend.netlify.app

No recrear recursos ni ejecutar smoke con registro de usuarios por esta tarea.
El merge `3e3ed95e74ff57c194767e717e374c7fbe118f2a` ya está desplegado y Live.
Health/readiness/OpenAPI respondieron 200; me sin token devolvió 401. No se creó
ninguna cuenta ni se modificó la base para comprobarlo.

## Arranque desplegado

[render.yaml](../render.yaml) usa `python scripts/start.py` y readiness
`/api/v1/ready`. El [launcher](../scripts/start.py):

1. valida settings y PORT;
2. abre un pool PostgreSQL con TLS según configuración de producción;
3. ejecuta la misma comprobación de disponibilidad/versión que readiness;
4. libera ese pool antes de iniciar el servidor, también ante error;
5. si falla, sale sin iniciar Uvicorn ni imprimir secretos;
6. inicia Uvicorn con un worker y access log desactivado.

No importa Alembic, no toma advisory locks ni ejecuta DDL. Render confirmó el
arranque del launcher del merge, preflight superado, Application startup complete
y escucha en 0.0.0.0:10000. No arrancar con Uvicorn directo para eludir el preflight:
en desarrollo es posible, pero producción debe conservar `python scripts/start.py`.

`/api/v1/health` no consulta DB. `/api/v1/ready` comprueba `SELECT 1` y que
`alembic_version` contenga solo `0002_auth_sessions`; si falla responde 503 sin
exponer detalles. No invoca Alembic, no aplica DDL y no verifica drift físico.

## Operación de migraciones y permisos

Database ejecutará el job de migración con un release inmutable, en la base
existente, antes del rollout backend. Un fallo cancela el rollout. Backend
verificará conexión/compatibilidad antes de escuchar y conservará readiness
durante ejecución. El proceso API usará credencial runtime sin permisos DDL.

El runner externo y la compatibilidad backend se validaron en PostgreSQL de CI,
permitiendo retirar Alembic local del runtime. Esto no acredita permisos o
recuperación de producción. El rollout de ese código ya ocurrió; la auditoría de
roles/grants y el ensayo de recuperación siguen siendo controles separados.
Evidencia final: [CI 38184856858](https://github.com/M1nzutt/cognova-backend/actions/runs/38184856858),
103 tests aprobados sin omisiones y runtime sin herramientas de migración.
La secuencia exacta y la política para futuras revisiones están en
[DATABASE_HANDOFF.md](DATABASE_HANDOFF.md). No se usa una comparación de strings
«mayor o igual» ni se acepta cualquier head por variable de entorno.

## Recursos y variables

El Blueprint contiene un bloque PostgreSQL y `fromDatabase`; no prueba que el
despliegue actual se haya creado desde él. El operador debe comprobar esa relación
antes de transferir la configuración a database. No aplicar otro Blueprint que
duplique la base; no borrar el recurso al limpiar el repositorio.

Variables runtime existentes, sin cambiar valores en esta fase:

| Variable | Responsabilidad |
| --- | --- |
| `DATABASE_URL` | Conexión backend a la base existente; secreta, TLS en producción; rol runtime tras el corte |
| `JWT_SECRET`, `JWT_ALGORITHM` | Solo backend; no requeridas por database |
| `ENVIRONMENT`, `PORT` | Entorno y puerto del servicio API |
| `CORS_ALLOWED_ORIGINS` | Array JSON de orígenes explícitos; conservar el frontend autorizado |
| `COOKIE_SECURE`, `COOKIE_SAMESITE` | Secure en producción y SameSite=Lax |
| `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` | Política auth vigente |
| `AUTH_RATE_LIMIT`, `AUTH_RATE_WINDOW_SECONDS` | Contadores persistentes de abuso |
| `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW` | Pool backend |
| `TEST_DATABASE_URL` | Exclusivamente PostgreSQL de pruebas; jamás producción |

El job database tendrá su propia credencial migradora en el gestor de secretos,
sin transmitirla al backend o frontend. No cambiar nombres de variables runtime
como parte de una separación documental.

## Incidente 404 cerrado: hostname incorrecto

La URL difundida con `1psi` (número uno) no pertenece al servicio inspeccionado:
responde texto `Not Found`, HTTP 404 y `x-render-routing: no-server`, sin
`X-Request-ID` de Cognova. El dashboard y el log de deploy publican `lpsi` (ele).
En esa URL, el mismo commit ya desplegado responde correctamente. No hubo cambio
de código runtime, configuración ni redeploy por este incidente.

Configuración efectiva leída del servicio `srv-db2j6nqj9qps73crqa0g`:

- Repo `M1nzutt/cognova-backend`, rama main, Root Directory vacío.
- Build: `pip install --require-hashes -r requirements.lock && pip install --no-deps .`.
- Start: `python scripts/start.py`; commit 3e3ed95; región Virginia; estado Live.
- Auto-Deploy On Commit; Health Check Path vacío; PR previews Off.
- El build instala cognova-backend 0.1.0 desde `/opt/render/project/src` y el
  runtime inicia Uvicorn sin fallar el preflight. El Blueprint versionado no
  representa todos los valores efectivos (región/auto-deploy/health check).

No reaplicar el Blueprint para corregir ese desfase. Configurar Health Check Path
como `/api/v1/ready` queda como ajuste operativo separado; no causa el typo de URL
ni fue modificado aquí. Un log `unmatched` sin la URL de petición no demuestra
que falten rutas API: distinguirlo de las respuestas HTTP verificadas.

Para evitar repetir el incidente, copiar el hostname mostrado por Render y usar
[el ejemplo de proxy corregido](../deploy/netlify.toml.example). El diagnóstico
[inspect_runtime.py](../scripts/inspect_runtime.py) muestra imports/versiones/rutas
sin exponer settings; la prueba de CI ejercita además el launcher real sobre TCP.

No hay nuevo endpoint de database ni variable para saltar la revisión requerida.
La referencia database fija para tooling se declara en
[tools/database-ref.json](../tools/database-ref.json); no es una configuración
runtime ni un mecanismo de ejecución automática de migraciones al desplegar API.

## Frontend y autenticación

Mantener Netlify `/api/*` → Render `/api/*`, mismo origen lógico para el navegador.
El ejemplo está en [deploy/netlify.toml.example](../deploy/netlify.toml.example).
Refresh: HttpOnly, Path=/api/v1/auth; CSRF: Path=/; ambos host-only y Secure en
producción. No cambiar cookies, DTOs, tokens o rutas por separar repositorios.
El agente frontend es responsable de su configuración y documentación.

## Validación y reversión del corte futuro

- Database: verificar backup/restauración, mismo destino, mismo historial/heads,
  no pérdida de filas ni secretos de sesiones y migración repetible sin recreación.
- Backend: CI con PostgreSQL real y artefacto database fijado; tests de auth,
  ownership, rotación, logout, concurrencia, rate limiting y readiness.
- Operación: health/readiness y smoke autorizado usando
  [scripts/smoke_auth.py](../scripts/smoke_auth.py). El smoke crea una cuenta sintética:
  no ejecutarlo como simple comprobación documental.
- No revertir DB automáticamente. Solo volver a un release backend compatible con
  el head aplicado; si aún no se hizo el corte, mantener el launcher actual.

No se afirma que backups, grants, CI remoto o compatibilidad de un runner externo
estén validados por esta documentación.
