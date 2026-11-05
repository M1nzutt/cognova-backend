# Cognova — Arquitectura Backend

## Calendario — decisión 2026-10-25, ampliado 2026-11-02

Calendario v1 separa router, DTO discriminado y servicio de consulta read-only.
Lee Actividades por deadline y Sesiones por planned_start_at con ownership y
paginación cronológica; no persiste copias ni necesita migración. Cambios siguen
pasando por los recursos originales. Ver CALENDAR_CONTRACT.

## Planes de Estudio + Retos — implementación backend 2026-11-03

El ORM refleja Database 0007; Database conserva DDL y grants. El router exige auth,
onboarding y ownership. `StudyPlanService` coordina transacciones y decisiones,
`StudyPlanResources` valida vínculos a registros originales y
`StudyPlanProjection` arma el detalle sin duplicar datos. Retos se operan solo bajo
un Plan y sus relaciones/contexto se validan antes de escribir. Los servicios usan
`LearningPlanMap`, `PriorityPlanner`, `DependencyNetwork`, `DecisionHistory`,
`WeeklyRhythm` y `StudySlots` en lógica de dominio. La interfaz del proveedor IA queda
preparada; Gemini no está conectado. El Backend que exige 0007 está Live en Render
desde el merge `d9fff7c36e6a1c1c98079e9be225c1d273e0e9d0`.

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

La implementación de la rama `feat/gemini-behavior` separa
`AcademicContext` (consultas acotadas por `user_id` y estructuras en memoria),
`GeminiProvider` (SDK/JSON Schema), `validate_proposal` (IDs/fechas/contexto),
`StudyPlanService` (transacción única de propuesta y Retos) y
`BehaviorAnalysisService` (umbral y observaciones de solo lectura). La clave
no entra en DTO ni Frontend. Database permanece en 0007; los textos de explicación
inicial del Plan son efímeros porque 0007 no tiene columnas para guardarlos.

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
- El launcher productivo exige conectividad y `0007_study_plans_and_challenges`
  antes de Uvicorn; readiness mantiene el mismo control sin depender de Alembic.
- Database 0007 y Backend Planes + Retos están desplegados. La rama Gemini no
  cambia schema ni revisión requerida. Ninguna instancia migra o repara esquema al
  arrancar (ver DEPLOYMENT y DATABASE_HANDOFF).
- Una revisión futura requiere coordinación de compatibilidad antes de aplicarse;
  consultar la secuencia de corte en [DATABASE_HANDOFF.md](DATABASE_HANDOFF.md)
  y el estado operativo en [DEPLOYMENT.md](DEPLOYMENT.md).

## Async/sync

La base actual usa SQLAlchemy síncrono.

Routers/servicios que ejecuten DB síncrona deben evitar bloquear innecesariamente el event loop.

No migrar toda la arquitectura a async sin motivo medido y documentado.
