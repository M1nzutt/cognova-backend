# Cognova — Estado del backend

Fecha local: 2026-10-11. Incidente 404 cerrado; backend operativo en Render.

## Estado Git y despliegue

- Handoff ya integrado en main: `3e3ed95e74ff57c194767e717e374c7fbe118f2a`.
- Render desplegó automáticamente ese commit; estado Live verificado en dashboard.
- Servicio existente: `srv-db2j6nqj9qps73crqa0g`; no se creó otro servicio o base.
- URL correcta: https://cognova-backend-lpsi.onrender.com — letra ele en `lpsi`.
- Rama de esta sesión: `fix/render-runtime-routing`; main/runtime no se modificaron.
- Inicio: árbol limpio, 19 commits. Cierre documental: aproximadamente 22 commits;
  verificar siempre con `git rev-list --count HEAD`.

La separación frontend/backend/database está realizada. No reiniciar handoff,
restaurar migraciones backend, ejecutar create_all ni usar CI como base del producto.
Database fijado en [database-ref.json](../tools/database-ref.json), commit
`0fe2c9eafedf1c44b5cd8d1c9dc998fbd9a7d5a1`. ORM/queries/auth permanecen en backend.

## Causa raíz demostrada

La URL del prompt/documentación usaba `1psi` (número uno). Ese hostname devuelve
404 text/plain, cuerpo `Not Found` y `x-render-routing: no-server`, sin request ID
Cognova. La petición no llega al middleware de la aplicación.

El dashboard y el log de deploy publican `lpsi` (letra ele). En ese host las rutas
funcionan sobre el mismo commit ya desplegado. No hubo que modificar imports,
factory=True, seguridad, DB o configuración Render; no se hizo redeploy innecesario.
Los logs históricos unmatched no contienen URL y no demuestran ausencia de rutas
API. No se añadió una ruta raíz artificial para esconder esos 404.

## Producción verificada

Smoke GET sin cuentas ni credenciales, 2026-10-11 23:26–23:29 America/Bogota:

| Ruta | Resultado |
| --- | --- |
| `/openapi.json` | 200, Cognova API y sus nueve paths documentados |
| `/api/v1/health` | 200, `{"status":"ok"}` |
| `/api/v1/ready` | 200, `{"status":"ready"}`; conexión/revisión DB compatible |
| `/api/v1/auth/me` | 401 INVALID_OR_EXPIRED_TOKEN sin token |
| `/api/v1/auth/sessions` | 401 sin token |
| GET de register/login/refresh/logout | 405, rutas existentes que requieren POST |

Las respuestas correctas incluyen X-Request-ID y headers de seguridad. Se conserva
Argon2id, JWT corto, refresh rotativo HttpOnly, CSRF, ownership y revocación. No se
crearon usuarios ni se hicieron escrituras de negocio o DDL productivos. Login,
restore y logout completos siguen requiriendo el smoke coordinado de frontend.

Configuración Render leída: repo M1nzutt/cognova-backend, branch main, Root Directory
vacío, build `pip install --require-hashes -r requirements.lock && pip install
--no-deps .`, start `python scripts/start.py`, región Virginia, Auto-Deploy On Commit,
Health Check Path vacío y PR previews Off. No se cambió configuración. El log confirma
wheel 0.1.0 desde `/opt/render/project/src`, preflight superado y Uvicorn en puerto10000.
Health Check Path `/api/v1/ready` es un ajuste de monitorización pendiente separado;
no fue la causa del typo. No reaplicar el Blueprint histórico para resolverlo.

## Cambios y evidencia

- `3c1ed8f`: diagnóstico [inspect_runtime.py](../scripts/inspect_runtime.py), prueba
  TCP de launcher y paso CI adicional para wheel aislado, cwd temporal/sin PYTHONPATH.
- `5dcc263`: URL documentada y [ejemplo proxy Netlify](../deploy/netlify.toml.example)
  corregidos. Ningún archivo frontend fue modificado.
- Cierre documental: actualiza estado, despliegue/arquitectura y decisiones obsoletas;
  el hash de ese commit aparece en git log.

[CI 38203767353](https://github.com/M1nzutt/cognova-backend/actions/runs/38203767353)
verde: **104 passed, 0 skipped**, incluidos 41 casos PostgreSQL; prueba adicional
sobre wheel instalado: **1 passed**. Ruff/formato, mypy (41 archivos), build,
auditoría y escaneo de secretos correctos. Una advertencia deprecación httpx de
Starlette TestClient sigue presente; no hay fallos.

El [CI de 5dcc263](https://github.com/M1nzutt/cognova-backend/actions/runs/38203945271)
también terminó en success. El último commit de esta sesión solo corrige estado
documental; no necesita repetir los controles del mismo código ya validado.

El diagnóstico en CI confirmó físicamente imports desde
`.local/runtime-check/lib/python3.14/site-packages/app/`, hashes de módulos iguales
al source, sys.path empezando en scripts/ y factory registrando los nueve paths.
Versiones: FastAPI0.142.2, Starlette1.7.0, Uvicorn0.54.0, distribución backend0.1.0.
Esto prueba el wheel/launcher; no se afirma haber ejecutado ese diagnóstico por
shell dentro de Render. El smoke productivo y logs sí se inspeccionaron directamente.

Local: Ruff/formato y build --no-isolation correctos; wheel coincide con source.
La inspección de imports local sigue bloqueada por Application Control en una DLL
SQLAlchemy. Se usó CI Linux, sin falsificar integración ni eludir la política.
No se modificaron repos hermanos, modelos, auth, contratos públicos, DB ni runtime.

## DEPENDENCY FRONTEND

Repo: cognova-frontend. Área: Netlify redirects/cliente REST y PROJECT_STATE.
Verificar `/api/v1/*` → `https://cognova-backend-lpsi.onrender.com/api/v1/*`
(con letra ele), ejecutar smoke real de login/restore/logout y actualizar su estado.
Si el proxy aún usa `1psi`, corregirlo allí con la URL verificada; este agente no lo
edita. Mantener mismo origen lógico, CSRF Path=/, refresh HttpOnly Path=/api/v1/auth,
Secure/Lax y access token solo en memoria. No rehacer auth frontend.

## Siguiente bloque funcional exacto

Tras el smoke frontend, coordinar academic_goal: sigue requerido en registro y User,
pero corresponde conceptualmente a pregunta1 del cuestionario. Antes de cambiarlo,
acordar compatibilidad DTO y transición de datos entre database/backend/frontend.
No se mueve aquí ni se crea una revisión nueva.

Cuestionario sigue bloqueado puntualmente: faltan opciones/IDs/valores aprobados,
cardinalidad single/multi, DTOs GET/POST/PUT, estado onboarding, errores y destino
tras completar. Las diez preguntas están aprobadas; no inventar el resto. Cerrar
esas decisiones antes del formulario definitivo. Si siguen pendientes, preparar
el contrato detallado de materias para revisión, sin implementar módulos con DTOs
supuestos. Conservar el roadmap funcional y avanzar en commits pequeños reales;
objetivo 300 commits por repo sin inflar ni sacrificar calidad.

Antes de reanudar: Git status/diff/log, referencia main real y documentación vigente.
El incidente 404 está cerrado; no seguir rediseñando infraestructura por él.
