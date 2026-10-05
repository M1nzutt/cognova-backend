# Cognova — Estado del Proyecto

**Estado:** fase inicial en curso; skeleton FastAPI creado (2026-10-05).

## Avance backend
- Factory FastAPI, router reservado `/api/v1`, configuración Pydantic desde `.env`.
- CORS configurable, paquetes por capa y pruebas de arranque/OpenAPI/CORS.
- Dependencias y guía local declaradas en `pyproject.toml` y README.
- Sin endpoints de negocio implementados; frontend sin modificaciones.

## Pendientes de especificación antes de funcionalidades
- API_CONTRACT.md enumera rutas pero no define requests/responses, códigos de
  estado, paginación ni validaciones por campo. Completar el contrato antes de
  implementar cada funcionalidad; no inventar campos alternativos.
- QUESTIONNAIRE.md no contiene opciones ni cardinalidad por pregunta.
- DATA_MODEL.md todavía no define persistencia de pausas del temporizador ni
  entidad de dependencias. Resolver antes de esas funcionalidades.

## Decisiones principales
- Frontend: React + TypeScript + Vite.
- Backend: Python + FastAPI.
- Base de datos: PostgreSQL.
- Dos repositorios separados.
- API REST.
- POO obligatoria.
- Una clase relevante por archivo.
- Código en inglés; interfaz en español.
- Multiusuario.
- Tema claro y oscuro.
- Estética: Notion + pastel suave + detalles cósmicos.
- IA real vía API.
- Mínimo 5 sesiones antes de hablar de patrones.
- Seed/demo data.

## Funcionalidades confirmadas
- Registro e inicio de sesión.
- Perfil: nombre, carrera, semestre, objetivo académico.
- Cuestionario obligatorio de 10 preguntas.
- Materias personalizables.
- Actividades con tipo, prioridad y fecha límite.
- Calendario visual.
- Temporizador.
- Estados: completed, partial, postponed, cancelled.
- Motivos predefinidos y personalizados.
- Historial, dashboard y racha.
- Acompañante IA conversacional limitado al contexto académico.
- Retos sugeridos por IA y aceptados/rechazados por el usuario.
- Grafo de dependencias académicas.

## Próximo paso
1. Completar infraestructura PostgreSQL y pruebas de ciclo de vida.
2. Cerrar la fase inicial sin implementar funcionalidades completas.
3. Posteriormente precisar contrato de autenticación y agregar User, migraciones,
   hashing y JWT mediante commits progresivos.

## Continuidad
Antes de trabajar, leer:
1. APP_CONTEXT.md
2. PROJECT_STATE.md
3. DECISIONS.md
4. API_CONTRACT.md
5. ARCHITECTURE.md
6. DATA_MODEL.md
7. DATA_STRUCTURES.md
8. AI_BEHAVIOR.md
9. AGENT_RULES.md

Si código y documentación se contradicen, no asumir: registrar y resolver.

## Validación del skeleton
- Python 3.14.5: 2 tests aprobados; Ruff y git diff --check correctos.
- Aviso de deprecación del TestClient de Starlette sobre httpx; sin fallos.
