# Cognova — Contrato de autenticación

Vigente 2026-10-12. Base /api/v1. La seguridad de sesión se conserva; el registro
se separa del onboarding. Contrato complementario: [ONBOARDING_CONTRACT](ONBOARDING_CONTRACT.md).

## Registro mínimo

POST /auth/register recibe exactamente:

```json
{"name":"Sara","email":"sara@example.com","password":"Example123!"}
```

Name obligatorio, trim/no vacío, máximo30 caracteres. Email obligatorio, formato
válido, normalizado/minúsculas, máximo50 y único case-insensitive. Password mínimo8,
máximo12 caracteres sin trim. Campos adicionales rechazados: degree_program,
semester y academic_goal ya no pertenecen al registro.

201 AuthResponse: {user:UserResponse,access_token:string,token_type:"bearer"}.
Crea User con campos académicos NULL, AuthSession y cookies; onboarding=incomplete.
Errores: 409 EMAIL_ALREADY_REGISTERED, 422 VALIDATION_ERROR, 429 TOO_MANY_REQUESTS,
403 FORBIDDEN si Origin no permitido. Ningún password/hash se expone.

## Usuario público y login

UserResponse compartido por registro, login, me y guardado académico:

```json
{
  "id": 1,
  "name": "Sara",
  "email": "sara@example.com",
  "degree_program": null,
  "semester": null,
  "onboarding": {
    "status": "incomplete",
    "academic_profile_complete": false,
    "questionnaire_complete": false,
    "next_step": "academic_profile"
  },
  "legacy_academic_goal": null
}
```

Legacy existente: legacy_academic_goal={value:string|null,captured_at:datetime},
leído del archivo inmutable 0003. No es q1 vigente ni completa onboarding. El objetivo
académico actual se consulta como q1 del cuestionario. No truncar datos históricos.

POST /auth/login: {email,password}, extra=forbid. Email normalizado; no aplicar
límites nuevos de registro a credenciales antiguas. 200 AuthResponse y nueva sesión.
401 INVALID_CREDENTIALS: "Correo o contraseña incorrectos." Tanto usuario inexistente
como clave incorrecta producen el mismo mensaje y ejecutan verificación Argon2.
Login/restauración/logout funcionan aunque onboarding esté incomplete.

GET /auth/me: Bearer requerido, 200 UserResponse; comprueba firma/expiración/type,
sub/sid, ownership y sesión existente no expirada ni revocada. 401
INVALID_OR_EXPIRED_TOKEN o SESSION_REVOKED. Estado onboarding centralizado en
OnboardingService, sin flags duplicados en frontend o columna inferida de texto vacío.

## Tokens y cookies

Argon2id para contraseñas con salts y rehash. Si una identidad legacy viola checks
NOT VALID de 0003, diferir rehash hasta remediación explícita para no romper login
por UPDATE incompatible; no truncar name/email ni desactivar los checks DB.

JWT HS256 access de 15 minutos por defecto, máximo15; solo memoria frontend.
Claims requeridas: sub (ID positivo string), sid (UUID), type=access, iat, exp;
jti aleatorio adicional. Sin email/datos sensibles. Algoritmo fijado en backend.

Refresh opaco <session_uuid>.<secreto aleatorio>, 48 bytes aleatorios; solo SHA-256
persistido. CSRF separado de32 bytes, hash asociado a sesión. Expiración absoluta
refresh30 días por defecto; rotar no amplía lifetime. Comparaciones constantes.

| Cookie | HttpOnly | Secure producción | SameSite | Path |
| --- | --- | --- | --- | --- |
| cognova_refresh | true | true | Lax | /api/v1/auth |
| cognova_csrf | false | true | Lax | / |

Host-only (sin Domain). Netlify proxyea /api/* a Render para un único origen lógico.
Frontend lee CSRF y lo envía en X-CSRF-Token. Nunca guardar tokens de auth en Web
Storage. CORS allowlist explícita con credenciales, nunca wildcard.

## Refresh y logout

POST /auth/refresh autentica únicamente por cookie refresh y X-CSRF-Token; no
acepta credencial refresh en JSON. Bloquea AuthSession, verifica vigencia, valida
cookie/header CSRF y hash asociado antes de comprobar hash refresh. Si CSRF antiguo
no coincide:403, no revoca sesión válida. Si secreto refresh incorrecto con CSRF
vigente: revoca persistentemente y devuelve401. Rotación atómica de ambos secretos,
last_used_at y nuevo access. 200 {access_token,token_type:"bearer"}.
Errores: INVALID_REFRESH_TOKEN/SESSION_REVOKED(401), CSRF_VALIDATION_FAILED(403),
TOO_MANY_REQUESTS(429). No se altera este flujo por onboarding.

POST /auth/logout: cookie refresh + CSRF; revoca sesión y limpia ambas cookies con
sus paths correctos. 204 sin cuerpo. Sin refresh cookie es no-op204 y limpia cookies;
con cookie exige CSRF. Repetir logout válido ya revocado devuelve204. Frontend borra
access de memoria; los access asociados a sid revocado ya no autorizan.

## Sesiones y autorización

GET /auth/sessions: Bearer, 200 lista de sesiones activas únicamente del propietario:
{id:UUID,created_at,last_used_at,expires_at,current}. Nunca hashes ni credenciales.
DELETE /auth/sessions/{session_id}: Bearer, ownership comprobado, 204; sesión ajena
/no encontrada=404 SESSION_NOT_FOUND, UUID inválido=422. Revocar sesión actual limpia
cookies cuando corresponden a esa sesión. Ninguno exige onboarding completo.

## Restauración y abuso

Al cargar: un refresh coordinado, token en memoria y GET /auth/me para conocer estado.
Ante401 repetir petición original solo una vez tras refresh; si falla, cerrar sesión,
sin bucles. Frontend navega usando onboarding.next_step, no adivina por strings.

Límites compartidos PostgreSQL: register/login/refresh por peer de red y además por
email en login; 20/60s por defecto, HMAC de claves, sin IP/email plano. No confiar en
X-Forwarded-For arbitrario. Contar fallos y devolver429 con Retry-After. Origin
se verifica cuando existe en register/login/refresh/logout. No-store y headers
seguros se mantienen en /api/*; errores no filtran payloads o secretos.

Formato general: {error:{code,message}}. 422 sin valores de input, 503 sin datos DB,
500 genérico. Domain errors de onboarding/cuestionario se definen en su contrato.
Variables existentes: JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
REFRESH_TOKEN_EXPIRE_DAYS, COOKIE_SECURE, COOKIE_SAMESITE, CORS_ALLOWED_ORIGINS,
AUTH_RATE_LIMIT y AUTH_RATE_WINDOW_SECONDS. No versionar secretos.
