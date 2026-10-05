# Cognova Backend

Backend de acompañamiento académico con Python, FastAPI y PostgreSQL.
Fase inicial: infraestructura; las funcionalidades de producto están pendientes.

## Entorno local

Requiere Python 3.11 o superior.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
.venv\Scripts\python -m uvicorn app.main:create_app --factory --reload
```

En macOS/Linux usar `.venv/bin/python` y `cp .env.example .env`.
Documentación interactiva: http://127.0.0.1:8000/docs.
No hay endpoints de negocio implementados ni endpoints provisionales.
El prefijo reservado es `/api/v1`, según [el contrato](docs/API_CONTRACT.md).

`CORS_ORIGINS` recibe un array JSON de orígenes explícitos. Por defecto se
deniega el acceso entre orígenes; el ejemplo habilita Vite local.
Los secretos deben quedar en `.env`, excluido de Git.

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
