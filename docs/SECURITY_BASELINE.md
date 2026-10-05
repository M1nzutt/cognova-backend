# Cognova — SECURITY_BASELINE.md

## Objetivo

Cognova se desarrolla con estándar de producción. Seguridad, privacidad, integridad de datos y recuperabilidad no son extras.

## 1. Autenticación

Obligatorio:
- Argon2id;
- access token corto en memoria;
- refresh token rotativo en cookie HttpOnly;
- sesiones revocables;
- logout real;
- CSRF;
- rate limiting;
- no tokens de autenticación en localStorage/sessionStorage.

La implementación detallada vive en `AUTH_CONTRACT.md`.

## 2. Autorización

Todos los recursos privados deben validar ownership en backend.

Nunca confiar en:
- `user_id` enviado por frontend;
- IDs de rutas sin comprobar propietario;
- ocultar botones como mecanismo de seguridad.

Debe haber tests explícitos donde usuario A intenta leer/modificar/eliminar datos de usuario B.

## 3. Validación

- Pydantic en límites de API.
- Validaciones de dominio en servicios/modelos.
- Constraints reales en PostgreSQL.
- Rechazar payloads inválidos y campos no permitidos cuando corresponda.
- Normalización consistente.

## 4. Secretos

Prohibido:
- API keys en frontend;
- secretos en Git;
- secretos en logs;
- valores reales en `.env.example`.

Usar variables de entorno y, en producción, secret manager si el proveedor lo permite.

## 5. CORS y HTTPS

- HTTPS obligatorio en producción.
- CORS con allowlist explícita.
- Nunca `*` con credenciales.
- Cookies `Secure` en producción.

## 6. CSRF

Obligatorio para acciones autenticadas mediante cookies, especialmente refresh y logout.

Seguir `AUTH_CONTRACT.md`.

## 7. XSS y frontend

- No usar `dangerouslySetInnerHTML` salvo necesidad documentada y sanitización robusta.
- No interpolar HTML no confiable.
- Configurar Content Security Policy en despliegue.
- Mantener dependencias actualizadas.
- Los tokens de autenticación no deben persistirse en Web Storage.

## 8. Rate limiting y abuso

Aplicar límites configurables a:
- auth;
- IA;
- endpoints costosos;
- operaciones susceptibles a abuso.

Responder `429` de forma consistente.

## 9. Base de datos

- PostgreSQL.
- Alembic para migraciones.
- Índices y constraints.
- Usuario DB con mínimo privilegio.
- Backups automáticos en producción.
- Procedimiento de restauración documentado y probado antes de considerar producción estable.

## 10. Logging

Logs estructurados.

No registrar:
- contraseñas;
- tokens;
- cookies;
- secretos;
- contenido sensible innecesario.

Asignar request/correlation ID cuando sea razonable.

## 11. Errores

- Handler global.
- Formato estable.
- No exponer stack traces al cliente en producción.
- Errores internos detallados solo en logs seguros.
- Mensajes de auth que no faciliten enumeración.

## 12. Dependencias

Antes de release:
- lockfiles;
- auditoría de dependencias;
- eliminar dependencias no usadas;
- revisar vulnerabilidades críticas/altas;
- documentar excepciones si una vulnerabilidad no puede corregirse inmediatamente.

## 13. IA

- API key únicamente backend.
- Verificar proveedor/modelo en documentación oficial antes de congelar decisión.
- Timeout.
- Retries limitados y con backoff cuando sean seguros.
- Límite de uso/costo.
- Validación de salida estructurada.
- No enviar datos que no sean necesarios para la tarea.
- Manejo claro de caída del proveedor.
- No inventar respuesta local fingiendo que vino de IA.
- No guardar conversaciones/datos de IA más tiempo del necesario sin decisión explícita.

## 14. Privacidad

- Minimización de datos.
- No almacenar dispositivo/IP en texto plano salvo necesidad justificada.
- Definir política de retención antes del despliegue público.
- Permitir borrar datos del usuario cuando esa funcionalidad se incorpore al alcance de producción.
- Los registros académicos pertenecen al usuario autenticado.

## 15. Observabilidad

Antes de producción:
- health/readiness checks;
- logging estructurado;
- monitoreo de errores;
- métricas básicas de disponibilidad/latencia;
- alertas razonables para fallos críticos.

## 16. CI/CD

Pipeline mínimo:
1. lint;
2. type/static checks;
3. unit tests;
4. integration tests;
5. build;
6. dependency/security scan;
7. secret scan.

No desplegar automáticamente si falla una etapa obligatoria.

## 17. Entornos

Separar:
- development;
- test;
- production.

No compartir:
- bases de datos;
- claves;
- cookies;
- secretos.

## 18. Checklist previo a producción

- [ ] Auth completa y probada
- [ ] Refresh rotation
- [ ] Revocación y logout
- [ ] CSRF
- [ ] Rate limiting
- [ ] Ownership tests
- [ ] CORS restrictivo
- [ ] HTTPS
- [ ] Security headers/CSP
- [ ] Error handling
- [ ] Logs seguros
- [ ] Integración PostgreSQL real
- [ ] Backups y restauración
- [ ] Dependency audit
- [ ] Secret scan
- [ ] IA real con timeout/cost controls
- [ ] Integration tests
- [ ] E2E crítico
- [ ] Health/readiness
- [ ] Variables de producción documentadas
