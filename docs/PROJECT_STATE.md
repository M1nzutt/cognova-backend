# Cognova — Estado del Proyecto (Backend)

Fecha de reconciliación: 2026-10-11.

## Fase 2 — evidencia nueva y adaptación en curso

- Backend inicial: `5fa90a3`, main limpio/sincronizado.
- Database hermano: `325e7ea6ec2981ed869a547c0c677fde1860e344`, limpio; solo lectura.
- Database remoto validado: `0fe2c9eafedf1c44b5cd8d1c9dc998fbd9a7d5a1`.
  [CI 38001623290](https://github.com/M1nzutt/cognova-database/actions/runs/38001623290)
  finalizó success, con PostgreSQL 17, pytest y verificación obligatoria sin skips.
  Respecto del checkout hermano solo cambia el título de README; no hay divergencia
  de código/historial. Los blobs de 0001/0002 coinciden también en una copia local
  del SHA remoto bajo `.local/`, dentro del backend.
- La compuerta database está superada por CI remoto. Esto no certifica grants,
  restauración o rollout de producción ni la suite backend modificada.
- Windows Application Control bloquea PostgreSQL local. No se intenta eludirlo;
  la validación online del backend se realizará en CI con base desechable.
- Preparadas fixtures externas con checkout limpio y SHA fijo declarado en
  `tools/database-ref.json`, guardas de destino local/DDL explícito y comparación
  ORM contra esquema externo. CI deja de aplicar el historial backend.
- En este primer bloque se conserva startup y copia local de migraciones hasta
  adaptar sus pruebas. No se toca producción ni el repositorio hermano.
- Verificación inicial: Ruff correcto (66 archivos); pytest no recopila la suite
  porque Windows Application Control bloquea `_processors_cy` de SQLAlchemy.
  No se interpreta como fallo de auth ni se desactiva la política del sistema.
  Se prepara una rama de revisión para ejecutar CI con PostgreSQL desechable;
  sin merge a main ni redeploy. Resultado remoto pendiente.

Las secciones siguientes conservan la referencia de la fase 1; esta sección
prevalece para el avance de fase 2.

## Estado confirmado

Al iniciar esta fase, `main` estaba limpio y sincronizado con `origin/main`, en
`06c3d2a feat: finalize production auth and deployment setup`. El documento anterior
estaba desactualizado: auth NO está limitada a fundamentos ni requiere rehacerse.

Código inspeccionado: User, AuthSession, RateLimitBucket, Argon2id, JWT corto,
registro/login/me, refresh rotativo, CSRF, logout real, sesiones/revocación,
ownership, rate limiting PostgreSQL, errores globales, security middleware,
health/readiness, ORM/conexiones, Alembic, CI, Render, launcher y smoke auth.

Commits base:
- `06c3d2a`: auth avanzada y preparación del despliegue.
- `96facf3`: modelo User y fundamentos de autenticación.
- `98e12bb`: configuración PostgreSQL.
- `a633870`: infraestructura FastAPI.
- `687100c`: diagnóstico, ownership de tres repositorios y contrato de entrega DB.

El bloque documental de operación complementa ese diagnóstico con README,
DEPLOYMENT, referencias de API y seguridad; no cambia el despliegue. Los enlaces
Markdown relativos fueron comprobados y no hay destinos inexistentes.

El usuario confirmó despliegue existente en Render, Render Postgres y Netlify:
[backend](https://cognova-backend-1psi.onrender.com) y
[frontend](https://cognova-frontend.netlify.app). Esta fase no ha comprobado tráfico,
revisión de producción ni grants, ni ha modificado o recreado esos recursos.

## Fase actual: preparar separación de database

Decisión vigente: tres repositorios, cognova-frontend, cognova-backend y
cognova-database. Este agente solo modifica documentación de cognova-backend.

Diagnóstico y contrato de entrega: [DATABASE_HANDOFF.md](DATABASE_HANDOFF.md).

- Backend conserva ORM SQLAlchemy, consultas, conexión, API, auth y lógica de negocio.
- Database es propietario definitivo de Alembic, historial, DDL, índices/constraints,
  seeds físicos, documentación del esquema y backup/restauración.
- La copia local de Alembic sigue operativa temporalmente para preservar deployment
  y pruebas; el traspaso físico NO se ha ejecutado ni se presenta como completado.
- Revisiones intactas: `0001_create_users` → `0002_auth_sessions`.
- Startup sigue migrando con advisory lock; readiness sigue exigiendo conectividad
  y la revisión exacta 0002. No se quitaron controles ni se introdujeron bypasses.
- El futuro runner database requiere configuración independiente de `app`, una
  versión fija, pruebas reales y coordinación antes de retirar la ejecución local.
- No se modificaron modelos, auth, DTOs, runtime, dependencias, CI ni Render.
- `academic_goal` continúa en User/auth. Corresponde conceptualmente a la pregunta 1
  del cuestionario; resolver después, con contrato y migración de datos coordinados.

## Validaciones

Referencia anterior informada por el usuario: Ruff correcto; pytest 55 passed,
40 skipped, 1 warning; build --no-isolation correcto. No equivale a integración
PostgreSQL desplegada verificada en esta fase.

Validación ejecutada en esta fase:
- `python -m pytest -q`: 55 passed, 40 skipped, 1 warning. Las omisiones requieren
  `TEST_DATABASE_URL`; la advertencia es deprecación httpx de Starlette TestClient.
- `ruff check app migrations scripts`: correcto.
- `ruff format --check app migrations scripts`: 63 archivos conformes.
- `git diff --check`: correcto; revisión del diff confirma cambios documentales.
- Blobs Git de ambas migraciones idénticos a `06c3d2a`, registrados en el handoff.
- El runner del editor no descubrió tests; se usó pytest directamente. El sandbox
  bloqueó inicialmente el intérprete externo; la ejecución autorizada sí completó.
- No se repitió build: ningún archivo ejecutable ni de empaquetado cambió.
No se usa SQLite ni se ejecutan tests que creen datos contra producción.

## Próximo paso exacto

1. El responsable de cognova-database recibe el historial de `06c3d2a`, verifica
   blobs/IDs y prepara configuración/runner independientes; detalles y pruebas
   de aceptación en [DATABASE_HANDOFF.md](DATABASE_HANDOFF.md).
2. Database valida base vacía, upgrade desde 0001 con datos, repetición segura,
   constraints/índices, grants y recuperación; publica commit/artefacto inmutable.
3. Backend consume esa versión en CI/fixtures, mantiene sus modelos y verifica
   auth/ORM con PostgreSQL real. Solo entonces preparar el cambio coordinado de
   startup sin DDL y el retiro del historial/dependencia local de Alembic.
4. Operación confirma propiedad de recursos Render existentes y coordina el corte
   sin crear otra base. Ver [DEPLOYMENT.md](DEPLOYMENT.md).

No avanzar ahora a cuestionario, materias, objetivos, actividades, sesiones,
temporizador, estructuras, analytics, Gemini ni retos. No tocar frontend/database
ni resolver fallos funcionales ajenos a esta separación.

## Reanudar

Leer Git y documentos antes de editar. Conservar cambios válidos. Esta fase prepara
la separación y deja dependencias explícitas; no afirma que el corte ya ocurrió ni
que el checklist global de producción está aprobado. Los commits documentales de
esta fase se identifican en `git log`; los cambios ejecutables base son `06c3d2a`.
