# Cognova Backend

Backend de acompañamiento académico con Python, FastAPI y PostgreSQL.
Autenticación avanzada y configuración de despliegue implementadas en `06c3d2a`.
La fase actual prepara la arquitectura de tres repositorios, sin nuevas funcionalidades.
Consultar [estado real](docs/PROJECT_STATE.md),
[traspaso de database](docs/DATABASE_HANDOFF.md) y [despliegue](docs/DEPLOYMENT.md).
ORM, consultas y conexiones permanecen en backend; Alembic y su historial se
conservan temporalmente aquí hasta que database valide su recepción y ejecución.

## Entorno local

Requiere Python 3.11 o superior y PostgreSQL (16 o superior recomendado).

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
# Editar DATABASE_URL y JWT_SECRET en .env antes de iniciar el servidor.
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:create_app --factory --reload
```

En macOS/Linux usar `.venv/bin/python` y `cp .env.example .env`.
Documentación interactiva: http://127.0.0.1:8000/docs.
Están implementados los siete endpoints de autenticación, health y readiness
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
disponibilidad PostgreSQL; el launcher de Render sí conecta para migrar antes de servir.
La dependencia `get_session` abre una sesión por petición, revierte
ante excepciones y siempre cierra; los servicios harán commit explícito.
No se usa `create_all`. Alembic conserva las revisiones `0001_create_users` y
`0002_auth_sessions`: users, sesiones revocables y contadores de rate limiting.
El launcher de Render todavía aplica migraciones antes de iniciar Uvicorn;
su retiro exige completar el [traspaso coordinado](docs/DATABASE_HANDOFF.md).

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

Las pruebas unitarias no necesitan un servidor. Para probar una conexión real,
definir `TEST_DATABASE_URL` con una base de pruebas PostgreSQL y ejecutar pytest.
La suite de integración crea y elimina esquemas aislados con Alembic y prueba auth
contra PostgreSQL real; se omite si falta esa variable. Nunca utilizar producción.
No utiliza automáticamente la base configurada en `.env`.

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
