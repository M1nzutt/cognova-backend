#  Cognova Backend

Backend de acompañamiento académico con Python, FastAPI y PostgreSQL.

## Estado del producto — 2026-11-20

La API implementa autenticación y sesiones, onboarding/cuestionario, Materias,
Actividades e historial, Sesiones/temporizador, Calendario, Planes/Retos,
Analytics, análisis de comportamiento IA y Acompañamiento académico con historial
persistente. Database posee las migraciones; Backend conserva ORM, autorización,
transacciones, lógica de negocio e integración Gemini. Ver [PROJECT_STATE](docs/PROJECT_STATE.md)
y [contratos](docs/API_CONTRACT.md).

La integración de código no equivale a un release remoto. En este checkout,
`ReadinessService` requiere Database `0010_nullable_password_hash`, pero
`tools/database-ref.json` aún fija el commit con revisión 0009. El volumen Docker
inspeccionado está en 0009. Hay que alinear el pin y validar migración, grants,
readiness y flujos con la imagen actual antes de declarar este checkout desplegado.
Render/Netlify se conservan como destinos de releases históricos; el estado actual
de despliegue está detallado en [DEPLOYMENT](docs/DEPLOYMENT.md).

La cuenta de demostración usa datos ficticios. El hash de contraseña no se incluye
en el seed: configúralo con el comando interactivo indicado en
[PERMANENT_DEMO](docs/PERMANENT_DEMO.md). El frontend muestra las credenciales
públicamente; configura la misma contraseña en el backend antes de la demostración.

API histórica: https://cognova-backend-lpsi.onrender.com (`lpsi` empieza con letra
ele, no número uno). No se verificó en este corte que esa URL sirva el código fuente
actual; no usarla como prueba del estado final de la integración local.

## Calendario v1 — consulta de recursos reales

GET /api/v1/calendar ofrece Actividades y Sesiones por rango, con filtros,
ownership, onboarding y paginación cronológica mixta. Solo consulta recursos
existentes; sin eventos libres, tablas ni migraciones. [Contrato](docs/CALENDAR_CONTRACT.md).
Este es uno de los módulos de la API; el índice completo está en
[API_CONTRACT](docs/API_CONTRACT.md).

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
Las rutas implementadas están bajo `/api/v1`; ver
[el contrato vigente](docs/API_CONTRACT.md).

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
No se usa `create_all`. El historial actual de Database termina en
`0010_nullable_password_hash`; el Backend fuente exige esa revisión. Sin embargo,
el pin del tooling y el volumen Docker inspeccionado todavía están en 0009. Resuelve
esa diferencia antes de ejecutar tests de integración o afirmar que el checkout está
desplegado. Ver [PROJECT_STATE](docs/PROJECT_STATE.md).
Materias: [contrato de API, catálogo y concurrencia](docs/SUBJECTS_CONTRACT.md).
`python scripts/start.py` valida disponibilidad y revisión 0010 antes de escuchar,
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
Si una prueba informa que el checkout no coincide, compara `git rev-parse HEAD` en
la ruta predeterminada `.local/database-handoff` con el SHA de `tools/database-ref.json`.
Una copia hermana correcta no se selecciona automáticamente: apunta a ella con
`COGNOVA_DATABASE_PATH` y confirma que esté limpia y en ese mismo SHA. No cambies el
pin ni adaptes el esquema para resolver una discrepancia de checkout.

IA, seed y cuenta de demostración forman parte del estado actual. Consulta
[PERMANENT_DEMO](docs/PERMANENT_DEMO.md) para las limitaciones de los datos demo y
la preparación de Gemini. Las notas de releases anteriores sobre estas funciones
fuera de fase son históricas.

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
