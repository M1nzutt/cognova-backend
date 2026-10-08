# Separación de cognova-database — diagnóstico y contrato de entrega

Fecha: 2026-10-08. Referencia inspeccionada: backend `06c3d2a`.
Estado: preparación documental; transferencia física y cambio de arranque pendientes.
Este documento no certifica el estado del repositorio database ni ejecuta operaciones allí.

## Responsabilidades

| Área | Propietario definitivo | Tratamiento en esta fase |
| --- | --- | --- |
| FastAPI, API, auth, ownership, servicios, analytics, estructuras, Gemini | backend | Conservar; no implementar nuevos módulos |
| SQLAlchemy ORM, queries, sesiones y conexión PostgreSQL | backend | Conservar todos los modelos y `app/database/` |
| Alembic, revisiones, DDL, constraints, índices, schema lifecycle | database | Preparar entrega; congelar historial local |
| Seeds físicos, backup/restauración, documentación física | database | Responsabilidad asignada; no existen implementaciones versionadas que transferir |
| UI, cliente HTTP, proxy Netlify | frontend | Sin cambios desde este agente; nunca acceso directo a PostgreSQL |

Las declaraciones de índices/constraints del ORM permanecen para representar el
esquema y detectar divergencias. No autorizan al backend a generar ni aplicar DDL.
Las reglas de validación y ownership siguen siendo responsabilidad del backend.

## Inventario comprobado

| Archivo o grupo | Dependencia actual | Acción en el traspaso |
| --- | --- | --- |
| [alembic.ini](../alembic.ini) | `script_location=%(here)s/migrations`, path local | Entregar y adaptar rutas en database |
| [migrations/versions/](../migrations/versions/) | Dos revisiones autocontenidas; importan SQLAlchemy y Alembic | Copiar íntegramente con sus IDs y contenido; nunca regenerarlas |
| [migrations/env.py](../migrations/env.py) | Importa `Settings`, `Base` y los tres modelos del backend | Database debe tener configuración propia, sin importar `app` ni necesitar JWT |
| [migrations/script.py.mako](../migrations/script.py.mako) | Plantilla de nuevas revisiones | Entregar a database |
| [scripts/start.py](../scripts/start.py) | `migrate()` importa Alembic, usa `alembic.ini`, aplica `head` | Trasladar la responsabilidad de `migrate()`; conservar launcher backend sin DDL después del corte |
| [app/database/](../app/database/) | Base declarativa, engine, pool, transacciones y dependencia por request | Mantener en backend |
| [app/models/](../app/models/) | `User`, `AuthSession`, `RateLimitBucket` | Mantener en backend; no mover ni duplicar ORM automáticamente |
| [readiness_service.py](../app/services/readiness_service.py) | SQL directo a `alembic_version`, revisión exacta | Mantener lectura y rechazo seguro; no necesita paquete Alembic |
| [render.yaml](../render.yaml) | Arranque con migración y recurso DB/fromDatabase | Conservar hasta coordinar propiedad de recursos existentes; no crear otra DB |
| [pyproject.toml](../pyproject.toml), [requirements.lock](../requirements.lock) | Alembic es dependencia runtime | Retirar solo después de eliminar imports productivos y preparar fixtures externas |
| [CI](../.github/workflows/backend.yml) | Lint de migrations, upgrade head, alembic check | Separar pruebas DDL a database; backend sigue probando ORM/API contra su release fija |

No hay seeds ni scripts de backup/restauración versionados. Archivos privados o
ignorados, credenciales, `.env` y datos locales no son parte de la entrega.

### Historial que debe conservarse

| Archivo | revision | down_revision | Blob Git en `06c3d2a` |
| --- | --- | --- | --- |
| `0001_create_users.py` | `0001_create_users` | `None` | `847886004b17e4b57723029cd217a63dd063d381` |
| `0002_auth_sessions.py` | `0002_auth_sessions` | `0001_create_users` | `ef8cd07f0a3482a272c5f62229f51a5390d74ec4` |

0001 crea `users`, índice `uq_users_email_lower` y constraint
`ck_users_semester_positive`. 0002 agrega `users.updated_at`, `auth_sessions`,
`rate_limit_buckets` y sus índices. La FK de sesiones elimina en cascada.
Conservar también los nombres: `AuthService` reconoce `uq_users_email_lower`
al convertir conflictos concurrentes a HTTP 409.

No squash, renumeración, recreación de tablas, `create_all`, `stamp head` ni
reescritura de revisiones aplicadas. La misma tabla `alembic_version` debe continuar
en la misma base y esquema. El cambio de repositorio no requiere una nueva revisión.

### Pruebas acopladas

- [integration/conftest.py](../app/tests/integration/conftest.py) crea un esquema
  `test_<uuid>`, ejecuta Alembic mediante conexión inyectada y elimina solo ese esquema.
  Todas las pruebas HTTP de integración dependen indirectamente de esta fixture.
- [test_user_migration.py](../app/tests/test_user_migration.py) valida SQL offline:
  debe pasar a database, junto con cobertura del historial completo.
- [integration/test_startup.py](../app/tests/integration/test_startup.py) comprueba
  que repetir migración conserva usuarios/sesiones: trasladar ese caso a database.
- [test_startup.py](../app/tests/test_startup.py) protege el fallo de migración:
  después del corte debe proteger fallo de disponibilidad/compatibilidad antes de servir.
- [test_health.py](../app/tests/test_health.py) e
  [integration/test_readiness.py](../app/tests/integration/test_readiness.py) permanecen:
  disponibilidad y compatibilidad son obligaciones del backend.
- [test_database.py](../app/tests/test_database.py) permanece: conexión, pool y rollback.

Quitar solamente `migrations/` o Alembic rompe el launcher, la fixture y CI.
Quitar la consulta de revisión haría perder una protección real del despliegue.

## Contrato inicial entre repositorios

1. **Versión fija:** database entregará un commit/tag inmutable más digest del
   artefacto, con cadena y head `0002_auth_sessions`. Backend registrará esa referencia
   explícita; CI nunca descargará automáticamente `main` ni un `latest` flotante.
2. **Ejecución independiente:** comando documentado de migración desde database,
   con URL mediante variable secreta, destino explícito y códigos de salida fiables.
   No depender de JWT, FastAPI, `Settings` ni imports de modelos del backend.
   Para reproducir las revisiones existentes puede usar `target_metadata=None`;
   no activar autogenerate sin una política propia de metadata y revisión DDL.
3. **Aislamiento de pruebas:** el runner debe soportar el esquema de prueba mediante
   una conexión o `search_path` controlado. No alterar `public` cuando la fixture
   pidió otro esquema. Solo usar bases desechables, nunca producción.
4. **Compatibilidad:** inicialmente backend acepta únicamente el conjunto de heads
   `{0002_auth_sessions}`. Revisión faltante, anterior, desconocida o múltiples heads
   da 503. Comparar conjuntos exactos; los IDs no tienen orden numérico/semántico.
   La comparación actual de una fila implementa esa política para el único head.
5. **Cambios futuros:** antes de aplicar una revisión nueva, pruebas conjuntas deben
   demostrar qué releases backend la toleran. Ampliar explícitamente los heads
   aceptados en un release backend compatible con esquema viejo y nuevo; desplegarlo
   antes de migrar. No introducir `EXPECTED_REVISION` arbitraria para saltar el control.
   Usar cambios aditivos y eliminación diferida; si no es posible, programar mantenimiento.
6. **No es garantía absoluta:** `alembic_version` detecta versión declarada, no drift
   ni permisos correctos. Database comprueba esquema físico y backend prueba sus
   consultas/auth contra el artefacto migrado; readiness no ejecuta DDL ni repara nada.
7. **Permisos:** rol migrador separado con DDL; rol runtime con DML necesario,
   secuencias, uso del esquema y SELECT de `alembic_version`, sin CREATE/ALTER/DROP.
   Database define grants actuales/futuros. No compartir el secreto migrador con backend.
8. **Entrega de configuración:** mantener endpoint/base/esquema existentes, TLS,
   nombres de tablas/constraints, tipos, nulabilidad, defaults y cascadas. Database
   documenta backup, restauración y retención; backend conserva su `DATABASE_URL`
   secreta. Frontend jamás recibe credenciales DB.

## Secuencia de corte segura

1. El responsable de database crea `cognova-database` y toma `alembic.ini`, plantilla
   e historial del commit `06c3d2a`, conservando trazabilidad de origen y blobs.
   Solo adapta su bootstrap/configuración. No copiar todo `app/`.
2. En PostgreSQL desechable, database valida: base vacía → 0002; base en 0001 con
   datos → 0002; repetir upgrade; historial/heads; constraints e índices; conservación
   de usuarios y hashes/sesiones existentes. Publica artefacto reproducible y evidencia.
3. Backend prepara un cambio separado que usa ese artefacto fijo para sus fixtures
   y CI, comprueba compatibilidad ORM/esquema y ejecuta todos los tests auth. No
   sustituirlos por mocks, no omitirlos para conseguir verde. El runner database
   puede conservar Alembic en un entorno de herramientas aislado, fuera del runtime API.
4. Antes del corte, el operador registra revisión efectiva, backup/restauración
   probada y recursos Render reales. El despliegue existente fue informado por el
   usuario; su revisión y grants no se han consultado en esta fase.
5. Database prueba su runner sobre la base ya en 0002 (upgrade sin cambios), sin
   añadir revisiones. Mantener congelado el esquema mientras hay launchers antiguos.
6. Backend despliega launcher sin `migrate()`: valida settings y DB/compatibilidad
   antes de escuchar; readiness sigue comprobándolo durante ejecución. Conserva
   respuestas públicas, cookies y auth. No instalar/importar Alembic en runtime.
7. Confirmar que no quedan instancias/jobs antiguos capaces de migrar. Transferir
   la operación DDL exclusivamente a database. Mantener exclusión mutua entre jobs
   (actual advisory lock `1943187001`), timeouts y abortar release ante fallo.
8. Retirar entonces del backend historial/config Alembic, dependencias y tests DDL
   ya entregados. Actualizar lock, CI, README y ownership de configuración Render
   en el mismo cambio coordinado. Validar health, readiness y auth tras el corte.

Durante el corte no se cambia esquema, IDs, datos ni DTOs. Si falla la preparación,
no se retira la copia local ni se modifica el arranque. Un rollback de backend solo
es válido contra un head admitido por ese release; no ejecutar downgrade destructivo
en producción como mecanismo automático de rollback.

## Dependencias pendientes fuera de backend

- **Database:** recibir/verificar archivos, publicar runner/release y evidencia,
  documentar esquema físico y grants, asumir migraciones, backups/restauración y
  coordinar propiedad de Render Postgres existente. No crear una base sustituta.
- **Frontend:** sincronizar la decisión de tres repos y mantener consumo de `/api/*`
  por Netlify. Esta separación no exige cambiar DTOs, cookies ni rutas del cliente.
  El agente frontend actualizará sus documentos; este agente no los modifica.
- **Operación:** confirmar quién administra el Blueprint actual antes de quitar
  su bloque `databases` o `fromDatabase`; la declaración versionada no acredita
  por sí sola cómo se crearon los recursos desplegados.

## Pendiente de producto separado

`academic_goal` sigue en User y auth por compatibilidad, aunque conceptualmente
corresponde a la pregunta 1 del cuestionario. Resolverlo después con contrato,
migración de datos y coordinación frontend/backend/database; no tocarlo aquí.
