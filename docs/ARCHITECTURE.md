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
