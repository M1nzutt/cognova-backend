# Despliegue existente y transición de base de datos

## Estado conocido

El usuario confirmó el 2026-10-08 estos recursos ya desplegados:

- Backend: https://cognova-backend-1psi.onrender.com
- PostgreSQL: Render Postgres (identificador, revisión aplicada y grants no
  inspeccionados en esta fase).
- Frontend: https://cognova-frontend.netlify.app

No recrear recursos ni ejecutar smoke con registro de usuarios por esta tarea.
La existencia informada del despliegue no equivale a una prueba funcional reciente.

## Arranque versionado actual

[render.yaml](../render.yaml) usa `python scripts/start.py` y readiness
`/api/v1/ready`. El [launcher](../scripts/start.py):

1. valida settings y PORT;
2. abre transacción PostgreSQL con TLS según configuración de producción;
3. establece lock_timeout de 30 s y statement_timeout de 120 s;
4. adquiere advisory lock transaccional `1943187001`;
5. ejecuta Alembic `upgrade head` con conexión inyectada;
6. si falla, sale sin iniciar Uvicorn ni imprimir secretos;
7. inicia Uvicorn con un worker y access log desactivado.

Este comportamiento sigue intacto durante la preparación del traspaso. Arrancar
con Uvicorn directamente no ejecuta esa migración. No cambiar comandos manualmente
para eludir el control mientras se coordina la separación.

`/api/v1/health` no consulta DB. `/api/v1/ready` comprueba `SELECT 1` y que
`alembic_version` contenga solo `0002_auth_sessions`; si falla responde 503 sin
exponer detalles. No invoca Alembic, no aplica DDL y no verifica drift físico.

## Arranque después del corte (pendiente)

Database ejecutará el job de migración con un release inmutable, en la base
existente, antes del rollout backend. Un fallo cancela el rollout. Backend
verificará conexión/compatibilidad antes de escuchar y conservará readiness
durante ejecución. El proceso API usará credencial runtime sin permisos DDL.

Antes de retirar Alembic local deben estar validados el runner externo, sus
permisos, aislamiento de fixtures y todos los tests de auth contra PostgreSQL real.
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
