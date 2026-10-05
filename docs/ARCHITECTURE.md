# Cognova — Arquitectura

```text
Usuario
  ↓
Frontend (React + TypeScript + Vite)
  ↓ HTTPS/JSON
Backend (Python + FastAPI)
  ├── PostgreSQL
  └── Servicio de IA
```

## Reglas
- Frontend solo consume backend.
- Frontend no toca DB ni IA.
- Backend concentra lógica, estructuras, persistencia e IA.
- Routers delgados; servicios con lógica.
- Una clase relevante por archivo.
- Repos: `cognova-backend` y `cognova-frontend`.

## Infraestructura inicial del backend
- Factory `app.main:create_app`; router `/api/v1` sin rutas de negocio todavía.
- Settings desde entorno/`.env`; CORS con orígenes explícitos.
- SQLAlchemy 2 síncrono con psycopg 3 para PostgreSQL.
- Un motor por lifespan, conexiones diferidas y cierre del pool al apagar.
- Sesión por petición mediante `app/database/dependencies.py`; commit explícito
  en servicios, rollback ante excepciones y cierre garantizado.
- Routers que ejecuten servicios síncronos de DB deberán ser `def` para evitar
  bloquear el event loop. Las futuras integraciones async requieren adaptación.
- `Base` centraliza metadata; modelos y migraciones quedan para la siguiente fase.
- Arranque y OpenAPI no prueban conectividad DB; prueba opcional con
  `TEST_DATABASE_URL` ejecuta `SELECT 1` sin modificar tablas.
