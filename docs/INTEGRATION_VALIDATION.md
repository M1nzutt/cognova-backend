# Validación de integración productiva

Fecha: 2026-10-17. Rama main. Onboarding desplegado y smoke aprobado.

## Runtime y permisos

Servicio srv-db2j6nqj9qps73crqa0g, base existente en 0003_onboarding_questionnaire.
Se inspeccionó DATABASE_URL efectiva en Render sin imprimirla: antes usaba
cognova_user propietario. Se creó cognova_runtime LOGIN NOINHERIT NOSUPERUSER
NOCREATEDB NOCREATEROLE NOREPLICATION y se actualizó únicamente DATABASE_URL.
Contraseña aleatoria generada en memoria, verificador SCRAM en PostgreSQL y
secreto almacenado en Render; nada versionado. Migrador/ownership sin cambios.

Permisos comprobados conectando con esa credencial al mismo recurso:

| Objeto | Permisos runtime |
| --- | --- |
| users, auth_sessions | SELECT, INSERT, UPDATE |
| rate_limit_buckets | SELECT, INSERT, UPDATE, DELETE |
| alembic_version, user_academic_goal_legacy | SELECT |
| questionnaire_responses | SELECT, INSERT |
| users_id_seq | USAGE, SELECT |
| Tres funciones de cuestionario/historia | EXECUTE |
| public | USAGE, sin CREATE |

Sin ownership ni UPDATE/DELETE de historia ni escritura de alembic_version.
Permisos de futuras tablas deben otorgarse deliberadamente, sin grants globales.
La comprobación local usó el endpoint externo del mismo recurso; Render conserva
el interno. El nuevo deploy cargó la conexión y pasó readiness y smoke real.

## Git, CI y deploy

- 40ed5baf8001d6a75c9a7010b3a67ff795900b14: smoke y preparación operativa.
- [CI previo 39077069939](https://github.com/M1nzutt/cognova-backend/actions/runs/39077069939): success.
  226 passed, 0 skipped; PostgreSQL real y control JUnit. Prueba adicional de wheel/
  launcher: 1 passed. Ruff/formato, mypy (76 archivos), build, pip-audit y gitleaks pasan.
- Local: 77 tests puros passed; Ruff y formato (109 archivos) correctos.
- Merge --no-ff, sin squash: 9309effdd1b71acc3fe5e24bc8c19b70c3d8c0c8.
  Árbol idéntico a la rama validada; historial de onboarding íntegro.
- Render deploy dep-db9vrie7bikc73e676q0: Live, mismo SHA del merge.
- [CI del merge 39077241478](https://github.com/M1nzutt/cognova-backend/actions/runs/39077241478): success;
  mismos 226 tests, launcher adicional y controles completos aprobados.

## Smoke real

Ejecutado scripts/smoke_auth.py contra https://cognova-backend-lpsi.onrender.com,
con Origin https://cognova-frontend.netlify.app. Credenciales/tokens/cookies solo
se mantuvieron en memoria; no se imprimieron cuerpos sensibles.

| Control | Resultado |
| --- | --- |
| GET /api/v1/health, /api/v1/ready | 200 / 200 |
| GET /openapi.json | 200; rutas onboarding presentes |
| GET /api/v1/auth/me sin sesión | 401 |
| Register mínimo / login / me | 201 / 200 / 200 |
| PUT academic-profile / GET catálogo | 200 / 200 |
| POST inicial / GET actual | 201 / 200, revisión 1 idéntica |
| PUT expected_revision=1 | 200, revisión 2 |
| Repetir expected_revision=1 | 409 |
| GET history | 200, revisiones [2,1], inicial intacta |
| GET me tras onboarding | 200, status complete |
| Refresh sin CSRF / válido | 403 / 200, refresh rotado |
| Me después de refresh / sesiones | 200 / 200 |
| Revocar otra sesión / access revocado | 204 / 401 |
| Logout / access después de logout | 204 / 401 |

Cookies: Secure ambas, refresh HttpOnly con Path=/api/v1/auth; CSRF no HttpOnly
con Path=/; ambas host-only y SameSite=Lax. Cache-Control no-store comprobado en
todas las respuestas API del smoke, incluidas errores y 204.
Verificación PostgreSQL READ ONLY adicional: 1 usuario sintético reciente,
2 sesiones, 0 sin revocar, 2 respuestas con revisiones [1,2]. La cuenta y su
historial permanecen deliberadamente; no se borran datos ni se fabrica limpieza.

## Alcance del cierre

Backend listo para frontend compatible con el contrato. No se desplegó ni modificó
frontend/database. E2E de navegador y proxy Netlify siguen a cargo del frontend;
este smoke HTTP no los sustituye. No volver a aplicar 0003 ni desplegar el backend
antiguo que exige 0002. HealthCheckPath de Render permanece vacío; no se cambió
configuración ajena al rol runtime. Inicio 54 commits; cierre 57, faltan 444 a 501.
