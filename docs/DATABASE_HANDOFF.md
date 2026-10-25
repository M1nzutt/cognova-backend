# Handoff database → backend

Materias y Actividades están cerrados en Backend. Schema productivo: `0005_activities`.
Siguiente módulo funcional: **Calendario**, con contrato aún por definir.
Este cierre no añade endpoints, DTOs, reglas ni implementación de Calendario.

Pin vigente: `604e296e2670d154ba7e18d7afa3f010e66dd42d`. Migración, grants y rollout
resueltos para estos releases; ver DEPLOYMENT e INTEGRATION_VALIDATION. Los
registros de corte/implementación conservan pendientes históricos, no bloqueos actuales.

Fecha histórica del corte inicial: 2026-10-11. Separación completada y mergeada en main (`3e3ed95`). Render
ya desplegó ese commit y sus rutas se verificaron. El diagnóstico de fase 1 se
conserva en `687100c`/`5fa90a3`; este documento conserva la trazabilidad del corte.

## Consumo 0005 — Actividades (2026-10-23)

Referencia: 604e296e2670d154ba7e18d7afa3f010e66dd42d, revisión 0005_activities.
Checkout aislado dentro de Backend; no se modifica el repositorio hermano.
Readiness/startup exigen exactamente 0005; no desplegar sobre 0004.
ORM conserva triggers como autoridad de fechas/revisión/historia. Runtime requiere
DML de activities, USAGE/SELECT de activities_id_seq y solo SELECT de eventos,
además de permisos existentes/lock users. Nunca EXECUTE de funciones trigger ni
escritura directa de historia. Database aplica migración/grants en release separado.
Contrato y rollback funcional: ACTIVITIES_CONTRACT. Las referencias siguientes
son históricas; no autorizan DDL runtime ni acreditan producción 0005.

Validación local histórica del 2026-10-23 (producción validada al día siguiente): 358 tests (124 PostgreSQL), ORM sin drift y preservación desde0004.
CI Backend40050090141 success sobre3f0c0cd992119aea985c1a23d6e271ea8b94faf2.
Rol local restringido verificado; esto no acredita grants de producción.

## Histórico — Consumo 0004 — Materias (2026-10-18)

Referencia vigente: c3394c38c55a8cd466d10f02fe7c80d7c1e1980f,
revisión exacta 0004_subjects. El checkout de pruebas aislado dentro de backend
fue actualizado a ese SHA y se verificó limpio. No se modifica el repo hermano.
ORM de Subject comparado contra PostgreSQL real sin drift; startup read-only y
readiness pasan. El código de esta rama rechaza 0003 hasta release coordinado.
Contrato público: [SUBJECTS_CONTRACT](SUBJECTS_CONTRACT.md). Operación debe aplicar
0004 y conceder SELECT/INSERT/UPDATE/DELETE en subjects, USAGE/SELECT de su secuencia,
y conservar permisos de lock users. DELETE explícito es parte del módulo pedido;
no TRUNCATE ni DDL runtime. No se cambiaron grants ni producción aquí.
CI final de Materias: [39196997553](https://github.com/M1nzutt/cognova-backend/actions/runs/39196997553),
completed/success sobre c62cde02bbeda0265e7723b604ac5f8abe099c72: 280 pruebas,
110 PostgreSQL, sin omisiones; runtime aislado y launcher del wheel aprobados.
Cierre 2026-10-19 solo documental; siguiente dependencia real es aplicar 0004 y
sus grants antes del release. No se desplegó ni cambió funcionalidad al cerrar.
Las referencias 0003 siguientes describen exclusivamente el handoff anterior.

## Referencia y evidencia histórica

Fuente de tooling fijada en [tools/database-ref.json](../tools/database-ref.json):
`M1nzutt/cognova-database` @ `232c43130c0fb3eddd32e1dd3707368ba0d87d4c`.
Esta rama de onboarding requiere `0003_onboarding_questionnaire`. La evidencia
de handoff 0002 siguiente es histórica; no cambia ni se repite esa fase.

## Histórico — Consumo 0003 — onboarding

- ORM de campos académicos nullable, archivo legacy y snapshots inmutables.
- Registro mínimo; q1 es el objetivo vigente. Legacy se conserva literalmente.
- Perfil/cuestionario producen estado explícito sin persistir flags duplicados.
- Backend inserta revisiones bajo bloqueo de User y expected_revision; no DDL.
- Startup/readiness rechazan 0002/desconocidas/heads múltiples en esta rama.
- Database/operación deben aplicar0003 y permisos sobre tablas nuevas antes del
  release coordinado. No se ha migrado producción desde backend ni se ha modificado
  el repositorio database. Anomalías históricas name/email fuera de límites requieren
  remediación explícita antes de actualizarse; login/lectura siguen disponibles.
- Contrato físico leído en el SHA exacto pedido, no en el commit documental28fa023.
- Contrato público: [ONBOARDING_CONTRACT.md](ONBOARDING_CONTRACT.md).

- Backend inició limpio en `5fa90a3`.
- Checkout hermano leído: `325e7ea6ec2981ed869a547c0c677fde1860e344`, limpio;
  no se hizo fetch, checkout ni escritura en él.
- El remoto está adelantado; solo cambia el título de README frente al checkout.
- [Database CI 38001623290](https://github.com/M1nzutt/cognova-database/actions/runs/38001623290)
  aprobó PostgreSQL 17, toda la suite y el control que rechaza skips/ausencia de
  integración. Se inspeccionaron workflow, tests y pasos realmente ejecutados.
- [Backend CI 38184426616](https://github.com/M1nzutt/cognova-backend/actions/runs/38184426616)
  aprobó fixtures externas, auth/ownership, concurrencia, ORM, startup read-only,
  readiness, Ruff, mypy, build y audit antes de retirar los archivos locales.
- [Backend CI final 38184856858](https://github.com/M1nzutt/cognova-backend/actions/runs/38184856858)
  aprobó el retiro completo en `842f2a4`: 103 tests sin skips, 40 de integración,
  instalación runtime sin Alembic/database, Ruff/mypy/build/auditoría y secretos.
  Detalle en [PROJECT_STATE.md](PROJECT_STATE.md).

El checkout hermano y sus documentos registraban resultados locales omitidos;
no se tomaron como certificación. La compuerta se superó con evidencia remota.
El ZIP local antiguo de database no se consume: se usa un checkout Git fijado por
SHA completo, verificado antes de ejecutar código y sin modificaciones/untracked.

## Integridad y continuidad

| Revisión | down_revision | Blob Git verificado en ambas copias y SHA remoto |
| --- | --- | --- |
| `0001_create_users` | `None` | `847886004b17e4b57723029cd217a63dd063d381` |
| `0002_auth_sessions` | `0001_create_users` | `ef8cd07f0a3482a272c5f62229f51a5390d74ec4` |

También coincidieron los SHA-256 de los archivos físicos antes del retiro.
El historial continúa íntegro en
[database/migrations](https://github.com/M1nzutt/cognova-database/tree/0fe2c9eafedf1c44b5cd8d1c9dc998fbd9a7d5a1/migrations).
No se crearon revisiones, no se alteraron IDs, ni se ejecutaron squash, stamp,
create_all, recreación del esquema o DDL de producción. La tabla alembic_version
permanece en la misma base/esquema.

## Distribución final de responsabilidades

| Responsabilidad | Repositorio |
| --- | --- |
| FastAPI/API, auth, autorización, ownership, servicios y lógica de negocio | backend |
| ORM SQLAlchemy, metadata, consultas, pool/conexión/transacciones PostgreSQL | backend |
| Analytics, estructuras, Gemini futuros | backend, fuera de esta fase |
| Alembic, historial, DDL, constraints/índices físicos y schema lifecycle | database |
| Seeds físicos, documentación física, backup/restauración | database |
| UI, cliente API, proxy Netlify; nunca acceso DB | frontend |

Se retiraron del backend `alembic.ini`, `migrations/` y el test SQL offline
`test_user_migration.py`, cuya cobertura está en database. El caso de repetición
DDL con datos también lo cubre database; el test backend de startup ahora comprueba
que una conexión read-only puede validar esquema sin modificar usuarios/sesiones.

[app/models/](../app/models/) y [app/database/](../app/database/) permanecen.
Los índices/constraints declarados en ORM sirven para mapping y detección de drift,
no para generar DDL. Sus nombres se conservan: auth depende de
`uq_users_email_lower` para traducir conflictos concurrentes a HTTP 409.

## Runtime y contrato de compatibilidad

[Startup](../scripts/start.py) valida settings/PORT y usa
[ReadinessService](../app/services/readiness_service.py) antes de Uvicorn. Libera
el pool en éxito/error; falla sin escuchar y sin imprimir secretos si DB no está
lista. No hay imports Alembic/database, advisory locks ni upgrade en runtime.

Readiness conserva SELECT 1 y lectura de alembic_version. Solo acepta una fila
`0005_activities`; ausencia, revisión distinta o múltiples heads dan503.
No hay variable de entorno para eludir esa decisión ni dependencia HTTP con
cognova-database, que no es un servicio. El identificador queda explícito en
ReadinessService y la referencia de tooling declara el mismo contrato.

Una nueva revisión exige pruebas de compatibilidad y un release backend que
admita explícitamente el conjunto de heads previsto antes de aplicar DDL.
No comparar IDs como versiones ordenables. Readiness verifica versión declarada,
no drift físico ni todos los permisos; CI compara ORM y prueba consultas reales.

## CI y desarrollo

[CI](../.github/workflows/backend.yml) lee el SHA fijado, descarga ese checkout
bajo `.local/database-handoff`, levanta PostgreSQL 17 desechable y ejecuta tests.
No consume main/latest. La fixture verifica checkout limpio/SHA y ejecuta el CLI
externo con URL del esquema aislado mediante entorno, sin JWT ni credenciales en
argv. No escribe en el checkout hermano; no hay fallback al historial backend.

Se requiere `TEST_DATABASE_URL` local desechable, sin opciones, y
`TEST_DATABASE_ALLOW_DDL=yes`; CI además exige `REQUIRE_POSTGRES_TESTS=1`.
Cada caso crea y elimina únicamente su esquema `test_<uuid>`. Nunca configurar
un túnel ni una URL de producción. El control JUnit rechaza skips, errores,
fallos y ausencia de integración.

Alembic 1.20.0 permanece únicamente en dependencias **dev**: ejecuta tooling de
pruebas y `compare_metadata` con el ORM backend. Se eliminó del lock runtime junto
con sus dependencias exclusivas. CI prueba además instalación runtime separada
sin Alembic/cognova_database. No usar un wheel database aislado: requiere checkout
completo con migraciones. Instrucciones reproducibles en [README](../README.md).

## Histórico — Rollout inicial y controles entonces restantes

Al cerrar fase 2 no se había desplegado. Posteriormente se mergeó 3e3ed95 y Render
lo desplegó automáticamente; durante el incidente de URL se verificaron Live,
OpenAPI/health/ready 200 y auth protegida. No se recreó DB ni se ejecutó DDL backend.

Operación/database aún deben acreditar los controles no verificados aquí:

1. Confirmar recursos Render existentes y quién administra el Blueprint; no
   aplicar otro que duplique o elimine PostgreSQL. El YAML backend se conserva
   sin cambios hasta esa coordinación.
2. Verificar revisión efectiva 0002 y backup/restauración probada.
3. Ejecutar migraciones desde el runner database fijado, con rol migrador; runtime
   recibe solo DML/secuencias/USAGE y SELECT de alembic_version, sin DDL.
4. Mantener backend compatible (3e3ed95 ya desplegado y comprobado); verificar que
   no queden instancias antiguas capaces de migrar antes de permitir revisiones nuevas.
5. Mantener serialización de jobs DDL (advisory lock 1943187001 en database), abortar
   rollout ante fallo y nunca hacer downgrade automático para revertir backend.

## Histórico — Dependencias externas del corte inicial

**DEPENDENCY DATABASE — operación/documentación:** el checkout hermano y su
PROJECT_STATE siguen registrando que no existe CI remoto aprobado. Su responsable
puede sincronizar esa evidencia; no bloquea el cambio de código porque se verificó
el remoto directamente. Rol migrador/runtime, grants, recuperación y operación
Render sí bloquean declarar completado el rollout productivo. No se modificaron
archivos database desde este agente.

Frontend debe consumir registro mínimo y UserResponse.onboarding. academic_goal
no está en registro ni como objetivo vigente de User; q1 vive en el cuestionario.
