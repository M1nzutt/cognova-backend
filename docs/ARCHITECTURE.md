# Cognova — Arquitectura Backend

```text
Usuario
  ↓
Frontend (React + TypeScript + Vite)
  ↓ HTTPS / JSON
Backend (Python + FastAPI)
  ├── PostgreSQL
  └── Proveedor de IA
```

## Límites

- Frontend solo consume API.
- Frontend no toca DB ni proveedor de IA.
- Backend concentra lógica de negocio, seguridad, estructuras, persistencia, analytics e IA.
- Dos repos: `cognova-backend` y `cognova-frontend`.

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
- Alembic;
- User + fundamentos de Argon2id/JWT iniciados.

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

La implementación anterior sin refresh/logout se considera obsoleta y debe migrarse, no ignorarse.

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

- migraciones Alembic;
- constraints;
- índices;
- backups;
- restauración documentada;
- usuario de mínimo privilegio.

## Async/sync

La base actual usa SQLAlchemy síncrono.

Routers/servicios que ejecuten DB síncrona deben evitar bloquear innecesariamente el event loop.

No migrar toda la arquitectura a async sin motivo medido y documentado.
