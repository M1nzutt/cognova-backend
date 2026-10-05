# Cognova — Estado del Proyecto (Backend)

**Fecha de referencia:** 2026-10-05

**Estado general:** backend en desarrollo. La autenticación quedó interrumpida durante una migración de alcance; hay fundamentos implementados, pero el flujo de producción NO está terminado.

## Regla crítica al reanudar

Antes de tocar código:

```bash
git status
git diff
git log --oneline -15
```

No asumir que un archivo quedó guardado/commiteado solo porque fue mencionado en una sesión anterior.

## Lo confirmado antes de la interrupción

Base backend:
- FastAPI factory;
- `/api/v1`;
- Pydantic settings;
- CORS configurable;
- SQLAlchemy 2;
- psycopg 3;
- PostgreSQL como DB objetivo;
- sesiones DB por request;
- Alembic;
- tests de infraestructura.

Commits confirmados de fase inicial:
- `a633870 chore: initialize FastAPI backend`
- `98e12bb feat: add database configuration`

Autenticación — primer bloque implementado antes del corte:
- `User`;
- migración Alembic inicial;
- schemas de auth;
- Argon2id;
- JWT HS256;
- tests de hashing/JWT/migración;
- documentación parcial.

En la última validación conocida de ese bloque se reportaron:
- 30 tests aprobados;
- 1 omitido por no disponer de PostgreSQL real;
- Ruff correcto;
- SQL de migración validado.

El hash del commit posterior de fundamentos de auth no está fijado en esta documentación; Git debe confirmarlo.

## Lo que NO debe darse por terminado

El trabajo se interrumpió antes de completar la autenticación.

No asumir completos:
- `POST /auth/register`;
- `POST /auth/login`;
- `GET /auth/me`;
- refresh;
- logout;
- AuthSession;
- CSRF;
- rate limiting;
- gestión/revocación de sesiones;
- endpoint tests finales;
- integración PostgreSQL real.

Además, el diseño anterior de auth (JWT largo + localStorage + logout local) quedó obsoleto.

## Nueva decisión de producción

Debe migrarse a `AUTH_CONTRACT.md` vigente:
- access token corto;
- access token solo en memoria;
- refresh token opaco rotativo HttpOnly;
- `AuthSession`;
- CSRF;
- logout/revocación;
- rate limiting;
- ownership.

Preservar código útil existente; no rehacer Argon2id/User/migraciones sin motivo.

## PostgreSQL

A la última comprobación conocida:
- no había `psql`/Docker/servicio PostgreSQL local disponible;
- prueba real con `TEST_DATABASE_URL` estaba omitida.

Antes de producción se requiere integración real con PostgreSQL.

## Gaps de contrato detectados

Antes de implementar funcionalidades posteriores:
- DTOs exactos de varios endpoints aún deben completarse;
- paginación/filtros de historial deben definirse;
- `QUESTIONNAIRE.md` tiene preguntas pero no contiene las opciones completas;
- el modelo de temporizador y dependencias fue ampliado en `DATA_MODEL.md`, pero código/migraciones aún deben implementarlo.

## Próximo paso exacto

1. Leer toda la documentación actualizada.
2. Inspeccionar Git.
3. Identificar cambios de auth existentes y no rehacerlos.
4. Completar migración a autenticación de producción.
5. Ejecutar suite completa.
6. Actualizar este archivo con archivos modificados, pruebas y commits.
7. Continuar por fases del prompt definitivo.

## Funcionalidades posteriores pendientes

- cuestionario;
- materias;
- objetivos;
- actividades;
- dependencias;
- sesiones/temporizador;
- estructuras de datos;
- analytics;
- historial;
- racha;
- IA real;
- observaciones;
- reflexiones;
- retos;
- seed;
- seguridad final;
- despliegue.

## Continuidad

Si se interrumpe otra vez:
- actualizar este documento antes de terminar;
- indicar siguiente paso exacto;
- dejar repo estable;
- no borrar trabajo no commiteado.
