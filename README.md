# Cognova Backend

Backend de acompañamiento académico con Python, FastAPI y PostgreSQL.
Fase inicial: infraestructura; las funcionalidades de producto están pendientes.

## Entorno local

Requiere Python 3.11 o superior y PostgreSQL (16 o superior recomendado).

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
# Editar DATABASE_URL en .env antes de iniciar el servidor.
.venv\Scripts\python -m uvicorn app.main:create_app --factory --reload
```

En macOS/Linux usar `.venv/bin/python` y `cp .env.example .env`.
Documentación interactiva: http://127.0.0.1:8000/docs.
No hay endpoints de negocio implementados ni endpoints provisionales.
El prefijo reservado es `/api/v1`, según [el contrato](docs/API_CONTRACT.md).

`CORS_ORIGINS` recibe un array JSON de orígenes explícitos. Por defecto se
deniega el acceso entre orígenes; el ejemplo habilita Vite local.
Los secretos deben quedar en `.env`, excluido de Git.

## PostgreSQL

Crear una base `cognova` y un usuario dedicado con permisos sobre esa base.
Configurar `DATABASE_URL=postgresql+psycopg://usuario:password@host:5432/cognova`
en `.env`; codificar los caracteres especiales del usuario/password para una URL.
No hay credenciales predeterminadas en el código. No se admite SQLite.

El motor se crea durante el lifespan de FastAPI y se libera al apagar.
Las conexiones son diferidas: iniciar el servidor no verifica disponibilidad de
PostgreSQL. La dependencia `get_session` abre una sesión por petición, revierte
ante excepciones y siempre cierra; los servicios harán commit explícito.
No se crean tablas automáticamente. Modelos y migraciones se añadirán con la
primera funcionalidad persistente; la infraestructura aún no aplica ownership.

Las pruebas unitarias no necesitan un servidor. Para probar una conexión real,
definir `TEST_DATABASE_URL` con una base de pruebas PostgreSQL y ejecutar pytest.
La prueba de integración ejecuta únicamente `SELECT 1`; se omite si falta esa
variable. Nunca utiliza automáticamente la base configurada en `.env`.

JWT, hashing, integración IA, seed y despliegue están pendientes de próximas fases.

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
