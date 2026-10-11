# Cognova — Estado del backend

Reconciliación: 2026-10-11. Fase 2 del handoff database → backend.

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

Validación posterior al retiro del historial y lock runtime: pendiente de CI de
este bloque. No declarar la rama final aprobada hasta registrar ese resultado.
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
- El siguiente bloque retira historial/runtime Alembic y sincroniza documentación;
  identificar su hash mediante git log.

## Próximo paso exacto

1. Completar CI de la retirada final, incluidas instalación runtime sin Alembic,
   tests PostgreSQL completos, Ruff/mypy/build/auditoría y revisión del diff.
2. Revisar la rama antes de merge; no desplegar automáticamente en esta fase.
3. Operación/database deben verificar 0002 efectiva, grants con rol runtime sin
   DDL, backup/restauración y ownership de recursos Render existentes. Solo entonces
   coordinar rollout y retirar launchers antiguos capaces de migrar. No crear otra DB.
4. El responsable de database puede actualizar su checkout/documentación local con
   la evidencia remota. No hay cambios de código database requeridos detectados.

[DEPLOYMENT](DEPLOYMENT.md) describe el despliegue informado existente y el corte
pendiente. No se certifican permisos, recuperación ni tráfico productivo aquí.
No avanzar a cuestionario, materias, sesiones, estructuras, IA ni otros módulos.
