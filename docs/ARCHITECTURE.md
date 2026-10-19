# Cognova — Arquitectura Backend

```text
Usuario
  ↓
Frontend (React + TypeScript + Vite)
  ↓ HTTPS / JSON
Backend (Python + FastAPI)
  ├── PostgreSQL
  └── Gemini (integración futura)

cognova-database (operación, no API de producto)
  └── Alembic / schema lifecycle / backups → PostgreSQL
```

## Límites

- Frontend solo consume API.
- Frontend no toca DB ni proveedor de IA.
- Tres repositorios: `cognova-frontend`, `cognova-backend` y `cognova-database`.
- Backend concentra lógica de negocio, seguridad, estructuras, analytics, IA,
  ORM SQLAlchemy, queries y conexiones/transacciones PostgreSQL.
- Database es propietario de Alembic, historial, DDL, constraints, índices, seeds
  físicos, documentación del esquema y backup/restauración. No reemplaza la API.
- Los modelos ORM permanecen en backend; sus declaraciones reflejan el esquema,
  pero no autorizan creación automática de tablas.
- Fase 2: historial y ejecución DDL retirados del código backend tras validar CI
  database y compatibilidad backend con PostgreSQL. El merge 3e3ed95 está desplegado
  y verificado en Render; consultar [DEPLOYMENT.md](DEPLOYMENT.md).

## Capas esperadas

```text
app/
├── api/
├── core/
├── database/
├── models/
├── schemas/
├── services/
├── structures/
│   └── nodes/
└── tests/
```

Reglas:
- routers delgados;
- servicios contienen casos de uso;
- acceso DB encapsulado;
- una clase relevante por archivo;
- dependencias explícitas;
- no lógica de negocio dispersa en routers.

## Infraestructura ya iniciada

- factory `app.main:create_app`;
- router `/api/v1`;
- settings desde entorno/`.env`;
- CORS configurable;
- SQLAlchemy 2 + psycopg 3;
- engine por lifespan;
- sesión DB por request;
- User, AuthSession y RateLimitBucket;
- auth HTTP completa implementada: Argon2id/JWT, refresh, CSRF y revocación;
- middleware de seguridad, errores, rate limiting y health/readiness;
- launcher sin DDL que exige DB disponible y esquema compatible antes de escuchar;
- tooling database fijado por commit para CI, fuera del runtime API.

El estado exacto vive en `PROJECT_STATE.md` y Git.

## Autenticación de producción

```text
login/register
   ↓
User + AuthSession
   ↓
Access JWT corto ─────────→ frontend memory
Refresh token opaco ──────→ HttpOnly cookie
CSRF token ───────────────→ cookie legible + header
```

`AuthSession` permite:
- refresh rotation;
- revocación;
- logout;
- gestión de sesiones;
- invalidar access tokens ligados a `sid`.

El diseño sin refresh/logout fue reemplazado en `06c3d2a`; no rehacerlo por
documentación antigua. La separación DB no cambia el contrato de autenticación.

## Seguridad transversal

Middleware/dependencias/servicios deben cubrir:
- auth;
- ownership;
- rate limiting;
- CORS;
- error handling;
- request IDs/logging;
- security headers cuando aplique.

Ver `SECURITY_BASELINE.md`.

## Temporizador

Backend es fuente de verdad.

El frontend puede mostrar un contador optimista, pero:
- start/pause/resume/finish se registran en backend;
- duración oficial se deriva de timestamps/intervalos persistidos;
- refrescar la página no debe perder el estado real.

## Estructuras de datos

Se implementan manualmente en backend y se integran en casos de uso reales.

La DB sigue siendo la fuente persistente; las estructuras no sustituyen PostgreSQL.

## IA

Flujo:

```text
datos persistidos
   ↓
analytics deterministas
   ↓
evidencia estructurada
   ↓
servicio IA
   ↓
salida validada
   ↓
observación / conversación / reto
```

La IA no debe calcular silenciosamente hechos que el backend puede obtener de forma determinista.

## Observabilidad

Producción debe contar con:
- health/readiness;
- logs estructurados;
- monitoreo de errores;
- métricas básicas;
- configuración por entorno.

## PostgreSQL

- Database administra migraciones Alembic, constraints, índices y recuperación.
- Backend conserva el ORM, consultas, transacciones y autorización por usuario.
- Rol migrador con DDL y rol runtime con DML deben separarse durante el corte.
- El launcher de esta rama exige conectividad y `0004_subjects` antes de
  Uvicorn; readiness mantiene el mismo control. No depende de Alembic para leerlo.
- Database migra antes del release; backend no migra ni repara esquema al arrancar.
  La separación se desplegó con3e3ed95; onboarding/0003 requiere release coordinado.
- Una revisión futura requiere coordinación de compatibilidad antes de aplicarse;
  consultar la secuencia de corte en [DATABASE_HANDOFF.md](DATABASE_HANDOFF.md)
  y el estado operativo en [DEPLOYMENT.md](DEPLOYMENT.md).

## Async/sync

La base actual usa SQLAlchemy síncrono.

Routers/servicios que ejecuten DB síncrona deben evitar bloquear innecesariamente el event loop.

No migrar toda la arquitectura a async sin motivo medido y documentado.
