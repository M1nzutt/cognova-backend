#  Cognova Backend

Backend de acompañamiento académico con Python, FastAPI y PostgreSQL.
Autenticación avanzada y configuración de despliegue implementadas en `06c3d2a`.
Esta rama incorpora Actividades sobre auth, onboarding y Materias existentes.
Contrato Actividades: [ACTIVITIES_CONTRACT.md](docs/ACTIVITIES_CONTRACT.md).
Consultar [estado real](docs/PROJECT_STATE.md),
[traspaso de database](docs/DATABASE_HANDOFF.md) y [despliegue](docs/DEPLOYMENT.md).
ORM, consultas y conexiones permanecen en backend; Alembic/historial viven en
cognova-database. Esta rama requiere 0005 y no se despliega automáticamente.

API verificada: https://cognova-backend-lpsi.onrender.com (`lpsi` empieza con letra
ele, no número uno). OpenAPI, health y readiness responden 200; auth exige token.

## Entorno local

Requiere Python 3.11 o superior y PostgreSQL (16 o superior recomendado).

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
# Editar DATABASE_URL y JWT_SECRET en .env antes de iniciar el servidor.
# El operador de cognova-database debe haber aplicado el esquema compatible.
.venv\Scripts\python -m uvicorn app.main:create_app --factory --reload
```

En macOS/Linux usar `.venv/bin/python` y `cp .env.example .env`.
Documentación interactiva: http://127.0.0.1:8000/docs.
Están implementados auth, health/readiness, perfil académico y cuestionario
bajo `/api/v1`, según [el contrato](docs/API_CONTRACT.md).

`CORS_ALLOWED_ORIGINS` recibe un array JSON de orígenes explícitos. Por defecto se
deniega el acceso entre orígenes; el ejemplo habilita Vite local.
Los secretos deben quedar en `.env`, excluido de Git.

## PostgreSQL

Crear una base `cognova` y un usuario dedicado con permisos sobre esa base.
Configurar `DATABASE_URL=postgresql+psycopg://usuario:password@host:5432/cognova`
en `.env`; codificar los caracteres especiales del usuario/password para una URL.
No hay credenciales predeterminadas en el código. No se admite SQLite.

El motor se crea durante el lifespan de FastAPI y se libera al apagar.
Las conexiones de la factory son diferidas: iniciar Uvicorn directamente no verifica
disponibilidad PostgreSQL; el launcher sí conecta para validar esquema antes de servir.
La dependencia `get_session` abre una sesión por petición, revierte
ante excepciones y siempre cierra; los servicios harán commit explícito.
No se usa `create_all`. Database conserva `0001_create_users` →
`0002_auth_sessions` → `0003_onboarding_questionnaire` → `0004_subjects` → `0005_activities`.
La referencia exacta requerida es 604e296e2670d154ba7e18d7afa3f010e66dd42d.
Materias: [contrato de API, catálogo y concurrencia](docs/SUBJECTS_CONTRACT.md).
`python scripts/start.py` valida disponibilidad y revisión 0005 antes de escuchar,
sin aplicar migraciones. Readiness mantiene esa protección durante ejecución.

## Configuración de autenticación

`JWT_SECRET` es obligatorio, sin valor predeterminado, con al menos 32 bytes.
Generar un valor local aleatorio con
`python -c "import secrets; print(secrets.token_urlsafe(48))"` y guardarlo en `.env`.
`JWT_ALGORITHM=HS256` y `ACCESS_TOKEN_EXPIRE_MINUTES=15` son los valores predeterminados.
No se aceptan algoritmos enviados por el cliente ni tokens sin expiración.
Usar HTTPS en despliegue para proteger contraseñas y tokens en tránsito.

Las contraseñas usan [Argon2id](https://argon2-cffi.readthedocs.io/en/stable/api.html)
y los tokens [PyJWT](https://pyjwt.readthedocs.io/en/stable/usage.html).
El contrato público vive en [AUTH_CONTRACT.md](docs/AUTH_CONTRACT.md).
Registro/login/me, refresh rotativo, logout, sesiones y revocación están implementados.

Registro solo name/email/password con límites 30/50/8–12. UserResponse expone
onboarding y campos académicos nullable; el login conserva credenciales históricas.
PUT /api/v1/onboarding/academic-profile guarda carrera/semestre. Cuestionario:
GET catálogo, POST inicial, GET vigente, PUT con expected_revision, GET historial
paginado. Revisión1 nunca se sobrescribe; el objetivo vigente es q1. Auth funciona
con onboarding incompleto; los futuros módulos académicos exigirán completitud.

Las pruebas unitarias no necesitan un servidor. Para probar una conexión real,
definir `TEST_DATABASE_URL` con una base de pruebas PostgreSQL y ejecutar pytest.
La suite de integración crea y elimina esquemas aislados usando el CLI de database
y prueba auth contra PostgreSQL real; se omite si falta esa variable. Nunca utilizar
producción, incluso mediante un túnel local. Requiere URL local sin opciones y
`TEST_DATABASE_ALLOW_DDL=yes`. CI impide omisiones.
No utiliza automáticamente la base configurada en `.env`.

Preparar una copia de tooling dentro del backend, fijada por
[tools/database-ref.json](tools/database-ref.json), sin tocar el checkout hermano:

```powershell
$databaseRef = Get-Content tools/database-ref.json | ConvertFrom-Json
git clone "https://github.com/$($databaseRef.repository).git" .local/database-handoff
git -C .local/database-handoff checkout --detach $databaseRef.commit
# Configurar TEST_DATABASE_URL con una base LOCAL desechable, nunca producción.
$env:TEST_DATABASE_ALLOW_DDL = 'yes'
$env:REQUIRE_POSTGRES_TESTS = '1'
.venv\Scripts\python -m pytest -q
```

El adaptador exige SHA exacto y checkout limpio; `COGNOVA_DATABASE_PATH` permite
seleccionar otra copia de tooling, siempre del mismo SHA. El CLI recibe el destino
por entorno sin JWT y con search_path del esquema aislado. Las dependencias dev
incluyen Alembic para tooling y comparación ORM; runtime y lock no lo incluyen.

IA, seed y demás módulos de producto están fuera de la fase actual. El despliegue
existente fue confirmado por el usuario; no se recrea durante la separación DB.

## Validación

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check .
```

## Organización

- `app/api`: routers delgados.
- `app/core`: configuración compartida.
- `app/database` y `app/models`: infraestructura y persistencia.
- `app/schemas` y `app/services`: validación y lógica de negocio.
- `app/structures/nodes`: nodos separados de las estructuras manuales.
- `app/tests`: pruebas del backend.

Una clase relevante por archivo. El frontend se desarrolla en otro repositorio.
Consultar [estado](docs/PROJECT_STATE.md) y [reglas](docs/AGENT_RULES.md)
antes de continuar.

### Validación de Actividades

La suite PostgreSQL crea únicamente esquemas test_<uuid> en servidor local desechable,
con TEST_DATABASE_ALLOW_DDL=yes y REQUIRE_POSTGRES_TESTS=1. La prueba de mínimo
privilegio requiere un administrador local capaz de crear/eliminar un rol temporal
(como PostgreSQL efímero de CI); nunca usar credenciales ni túneles de producción.
El checkout .local/database-handoff debe estar limpio en el SHA completo de tools/database-ref.json.
El rol runtime productivo nunca debe recibir privilegios administrativos de pruebas.
