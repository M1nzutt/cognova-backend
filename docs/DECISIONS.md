# Cognova — Decisiones Congeladas

## Producto

- Nombre: Cognova.
- Aplicación web multiusuario.
- Propósito: acompañamiento académico basado en evidencia.
- No es un chatbot genérico ni una herramienta terapéutica.
- Interfaz en español; código interno en inglés.
- Aplicación desplegada y funcional.
- Calidad objetivo: producción; no se aceptan atajos por tratarse de una entrega académica.

## Stack

- Backend: Python + FastAPI.
- Frontend: React + TypeScript + Vite.
- DB: PostgreSQL.
- API REST.
- Tres repositorios: cognova-frontend, cognova-backend y cognova-database.
- Backend es el único acceso de la aplicación a PostgreSQL y Gemini. Database
  accede con herramientas operativas para migraciones/recuperación; frontend nunca.

## Código

- POO obligatoria.
- Una clase relevante por archivo.
- Responsabilidades separadas.
- Nivel técnico intermedio/alto sin sobreingeniería innecesaria.
- Estructuras de datos implementadas manualmente y usadas de verdad.

## Funcionalidad

- Perfil: nombre, carrera, semestre, objetivo académico.
- Materias personalizables.
- Actividad genérica con `type`.
- Prioridades manuales y deadlines.
- Calendario visual.
- Temporizador integrado con backend como fuente oficial.
- Motivos predefinidos + personalizados.
- Cuestionario obligatorio de 10 preguntas.
- IA como acompañante académico.
- IA automática con evidencia suficiente y manual bajo demanda.
- Mínimo 5 sesiones antes de hablar de patrones.
- Retos: IA propone, usuario acepta/rechaza; aceptado no se edita.
- Gamificación: únicamente racha.
- Grafo: dependencias académicas.
- Sin pantalla especial para estructuras.
- Seed/demo reproducible.
- Diseño: Notion + pastel + detalles cósmicos discretos.
- Tema claro y oscuro.

## Autenticación — decisión vigente 2026-10-05

Reemplaza el diseño anterior de JWT persistido.

- Argon2id para contraseñas.
- Access token JWT corto (10–15 min objetivo).
- Access token solo en memoria del frontend.
- Refresh token opaco rotativo en cookie HttpOnly.
- Hash del refresh token persistido.
- AuthSession revocable.
- Logout real.
- CSRF en operaciones dependientes de cookie.
- Rate limiting.
- CORS restrictivo.
- HTTPS obligatorio en producción.
- Ownership backend obligatorio.
- No tokens de autenticación en localStorage/sessionStorage.

`AUTH_CONTRACT.md` es la fuente de verdad para detalles.

## IA

- IA real vía API.
- Proveedor/modelo se congela solo después de verificar documentación oficial vigente.
- API key únicamente backend.
- Timeouts, límites de uso/costo y manejo de fallo obligatorios.
- Nunca fingir respuesta de IA con texto local.

## Persistencia y despliegue

- Alembic administra esquema bajo ownership de cognova-database. Su alojamiento
  y ejecución actuales en backend son transitorios hasta completar el traspaso.
- No `create_all` automático en producción.
- Entornos dev/test/prod separados.
- Backups y procedimiento de restauración antes de declarar producción estable.
- CI con pruebas, build y controles de seguridad.

## Cambios a decisiones congeladas

### Tres repositorios y separación DB — 2026-10-08

- Sustituye la decisión de dos repositorios. Backend conserva ORM SQLAlchemy,
  conexiones, queries, servicios, API, auth y ownership; database posee Alembic,
  historial, DDL, índices/constraints, seeds físicos y backup/restauración.
- No mover automáticamente modelos ORM ni sustituir migraciones por `create_all`.
- Conservar exactamente `0001_create_users` → `0002_auth_sessions`, sin squash,
  renumerar, recrear esquema ni marcar revisiones como aplicadas artificialmente.
- Se prepara el traspaso en [DATABASE_HANDOFF.md](DATABASE_HANDOFF.md). Esta fase
  no modifica startup, readiness, CI, Render ni dependencias ejecutables: el runner
  externo y su release aún requieren validación por el repositorio database.
- El backend dejará de ejecutar migraciones al arrancar tras ese corte coordinado;
  mantendrá verificación de DB y compatibilidad. No basta comprobar `SELECT 1`.
- Mantener el despliegue existente. No crear otra DB ni aplicar de nuevo el Blueprint.
- `academic_goal` corresponde conceptualmente a la pregunta 1 del cuestionario;
  permanece en User y auth hasta un refactor posterior con migración y contratos.
- Cada agente modifica solo su repositorio. Las dependencias con los otros se
  documentan; no se editan archivos externos para sincronizar unilateralmente.

### Implementación de auth revocable — 2026-10-05
- Se conserva la migración 0001; 0002 agrega sesiones UUID, updated_at y contadores
  de abuso. Los JWT antiguos sin sid/type/iat se rechazan; se requiere nuevo login.
- JWT: 15 minutos por defecto, máximo 15; refresh: 30 días absolutos, sin extender
  expiración al rotar. Se incluye jti aleatorio para distinguir emisiones.
- Refresh/CSRF: 48/32 bytes aleatorios respectivamente, SHA-256 de los secretos
  en DB y comparaciones constantes. No se requiere hashing lento para secretos
  aleatorios de alta entropía. Argon2id se mantiene para contraseñas humanas.
- Rotación y revocación serializadas con SELECT FOR UPDATE. CSRF se valida antes
  del secreto conforme al contrato: replay con CSRF antiguo da 403; secreto
  antiguo con CSRF vigente revoca de forma persistente y da 401.
- Rate limiting compartido en PostgreSQL: ventana por IP y adicional por email
  en login, 20 intentos/60 segundos por defecto, configurable. Las claves usan
  HMAC-SHA256, nunca IP/email plano. Intentos fallidos también consumen cuota.
- No se confía directamente en X-Forwarded-For; configurar proxies confiables en
  Uvicorn al desplegar. El limitador falla cerrado si PostgreSQL no está disponible.
- Registro/login verifican Origin cuando existe, para impedir login CSRF.
- Logout sin refresh cookie es no-op 204; con cookie exige CSRF asociado. Revocar
  una sesión ajena devuelve 404 sin revelar existencia. DELETE devuelve 204.
- Decisión confirmada por el usuario: CSRF Path=/; refresh HttpOnly Path=/api/v1/auth.
  Netlify proxyea /api/* hacia Render conservando /api/*; mismo origen lógico,
  cookies host-only, Secure y SameSite=Lax. No hace falta SameSite=None.

Solo mediante:
1. motivo claro;
2. impacto documentado;
3. actualización de contratos/docs;
4. migración de código y pruebas.
