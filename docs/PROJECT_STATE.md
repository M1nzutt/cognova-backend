# Cognova — Estado del backend

Reconciliación: 2026-10-11. Incidente de rutas públicas en Render.

## Incidente actual — diagnóstico en curso

- Main inicial: `3e3ed95e74ff57c194767e717e374c7fbe118f2a`, limpio, 19 commits.
  Handoff ya mergeado; el usuario confirmó deploy Live con preflight/Uvicorn correctos.
  Las referencias a rollout pendiente más abajo corresponden al cierre histórico
  de la fase anterior y no deben usarse para reiniciar el handoff.
- Rama de diagnóstico: `fix/render-runtime-routing`.
- GET directo a la URL informada `https://cognova-backend-1psi.onrender.com`:
  OpenAPI, health, ready y me devuelven 404. Captura con curl: cuerpo `Not Found`,
  Content-Type text/plain, `x-render-routing: no-server`, sin X-Request-ID Cognova.
  Este 404 observado está en la capa de routing Render; aún falta inspeccionar el
  servicio real para determinar la causa de no-server. No atribuirlo a imports.
- El wheel local coincide con source para app/__init__, app/main, api/router y
  api/health. Solo la distribución cognova-backend declara top-level app.
- La inspección Python local sigue bloqueada por Windows Application Control en
  SQLAlchemy; se valida en CI, sin eludir políticas ni usar producción para tests.
- Añadidos diagnóstico seguro de imports/rutas y prueba TCP del launcher real,
  repetida en CI desde un wheel aislado, cwd temporal y sin PYTHONPATH del source.
  Así se distingue TestClient de Uvicorn/packaging. No cambia runtime ni auth.
- Render accesible al agente muestra login, sin otras pestañas compartidas ni
  RENDER_API_KEY configurada. Se pidió acceso a la sesión que indicó el usuario;
  configuración efectiva, commit/logs Render y cualquier redeploy siguen pendientes.

Siguiente paso inmediato: ejecutar CI de la reproducción y contrastar URL/config
del servicio Render existente. No crear recursos ni modificar DDL/auth por hipótesis.

Actualización: Render ya es accesible. Servicio srv-db2j6nqj9qps73crqa0g, main
3e3ed95 Live; URL real `https://cognova-backend-lpsi.onrender.com`, letra ele en
lpsi. La URL con número uno era incorrecta. Smoke directo: OpenAPI/health/ready
200 y me sin token 401. No hace falta redeploy ni cambio runtime. Se corrige la
URL documentada y el ejemplo de proxy backend. CI de la nueva prueba HTTP en curso.

## Estado real y alcance

Backend inició limpio en `5fa90a3`, main sincronizado. Auth avanzada y deploy
existían desde `06c3d2a`; no se rehicieron. El trabajo actual está en
`chore/database-handoff-phase2`, sin merge a main ni redeploy.

- Separación física: database existe y recibió 0001/0002 sin cambios de IDs/contenido.
- Validación PostgreSQL database: confirmada en CI remoto con rechazo obligatorio
  de omisiones; no se usó PostgreSQL productivo.
- Adaptación backend: fixtures externas, compatibilidad ORM y startup sin DDL.
- Retiro en código: alembic.ini, migrations/ y test SQL offline transferido; Alembic
  deja runtime/lock y permanece en dev para tooling de tests/compare_metadata.
- Corte operativo productivo: PENDIENTE. No cambios Render, grants, datos, recursos,
  frontend o repo hermano database. El Blueprint histórico no se ha reaplicado.

## Referencia database y evidencia

Checkout hermano inspeccionado solo en lectura:
`325e7ea6ec2981ed869a547c0c677fde1860e344`, limpio. Su documentación de pruebas
locales estaba atrasada respecto al remoto; no se hizo fetch ni se escribió allí.

Referencia adoptada: `0fe2c9eafedf1c44b5cd8d1c9dc998fbd9a7d5a1`, declarada en
[tools/database-ref.json](../tools/database-ref.json). Respecto del checkout hermano
solo cambia el título README. Se verificaron blobs y SHA-256 de ambas revisiones
antes de retirarlas; valores y contrato en [DATABASE_HANDOFF](DATABASE_HANDOFF.md).

[Database CI 38001623290](https://github.com/M1nzutt/cognova-database/actions/runs/38001623290):
success con PostgreSQL 17. Cubre vacío→head, 0001→0002 con datos, revisión,
repetición, constraints/índices, cascada, rollback y search_path.

[Backend CI 38184426616](https://github.com/M1nzutt/cognova-backend/actions/runs/38184426616):
success antes del retiro local. Auth/ownership/concurrencia, fixtures externas,
compatibilidad ORM y startup read-only ejecutados con PostgreSQL real, sin skips;
Ruff, formato, mypy, build, auditoría y escaneo de secretos aprobados.

Validación final tras el retiro, commit `842f2a4fad54d0e553f98c7d864da92db64fa2af`:
[Backend CI 38184856858](https://github.com/M1nzutt/cognova-backend/actions/runs/38184856858)
completado success. **103 passed, 0 skipped, 1 warning**, incluidos 40 casos de
integración PostgreSQL según el control JUnit. Mypy: sin problemas en 41 archivos.
Ruff/formato, build, escaneo de secretos y auditoría aprobados (sin vulnerabilidades
conocidas). La instalación runtime aislada confirma ausencia de Alembic y
cognova_database y permite importar factory/launcher. La advertencia pendiente
es deprecación httpx de Starlette TestClient; no hay fallos de tests.
El commit posterior a esa validación solo registra evidencia documental, sin
cambios de código/dependencias. No requiere repetir el CI ya aprobado.
Ruff/formato local: correctos, 62 archivos. Build --no-isolation genera sdist y
wheel correctamente. El diff del lock solo retira Alembic/Mako/MarkupSafe y sus
referencias; no cambia versiones de otras dependencias.

## Cambios preservados y límites

User, AuthSession, RateLimitBucket, ORM, queries y API permanecen. Auth conserva
Argon2id, JWT corto, refresh opaco rotativo, CSRF, revocación/logout y ownership.
`academic_goal` no cambia; su traslado conceptual a cuestionario pregunta 1 es
posterior. No hay nueva revisión ni módulos de producto.

Startup verifica DB/esquema antes de escuchar y libera el pool. Readiness exige
explícitamente una única revisión 0002. Database no es servicio HTTP ni import
runtime. Tests usan su CLI desde checkout limpio fijado, con credenciales solo por
env y esquemas desechables; backend CI ya no ejecuta migraciones locales.

Dos incidencias detectadas al activar CI se corrigieron sin cambio funcional:
- Mypy: nombre separado para ReturningInsert en rate limiting; misma consulta SQL.
- Test de privacidad del log: acepta plantilla estática relativa del router, además
  de absoluta; mantiene comprobación del endpoint HTTP y ausencia de secretos.

Localmente Windows Application Control bloquea PostgreSQL y DLL de SQLAlchemy:
pytest completo no logra recopilar (9 errores de importación en el primer intento).
No se eludió esa política ni se confundió con un fallo de auth. Dos tests aislados
del adaptador sí pasaron. Ruff y formato locales pasan. CI Linux es la evidencia
real de suite completa, en vez de presentar skips o mocks como integración.

## Commits de esta fase

- `b170b1a`: tooling database fijado, fixtures externas y comparación ORM.
- `9a9d818`: startup sin DDL y pruebas de fallo seguro/read-only.
- `e8e0bd8`: correcciones mínimas de tipado y aserción de ruta de log.
- `842f2a4`: retiro de historial/runtime Alembic, lock y documentación; CI final verde.

## Próximo paso exacto

1. Revisar la rama validada antes de merge; no desplegar automáticamente en esta fase.
2. Operación/database deben verificar 0002 efectiva, grants con rol runtime sin
   DDL, backup/restauración y ownership de recursos Render existentes. Solo entonces
   coordinar rollout y retirar launchers antiguos capaces de migrar. No crear otra DB.
3. El responsable de database puede actualizar su checkout/documentación local con
   la evidencia remota. No hay cambios de código database requeridos detectados.

[DEPLOYMENT](DEPLOYMENT.md) describe el despliegue informado existente y el corte
pendiente. No se certifican permisos, recuperación ni tráfico productivo aquí.
No avanzar a cuestionario, materias, sesiones, estructuras, IA ni otros módulos.
