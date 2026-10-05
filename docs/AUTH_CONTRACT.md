# Cognova — Contrato de Autenticación de Producción

## 1. Objetivo

Este contrato es la fuente de verdad compartida entre frontend y backend para autenticación y gestión de sesión.

Principios obligatorios:

- contraseñas con Argon2id;
- access token JWT de corta duración;
- access token guardado solo en memoria del frontend;
- refresh token opaco y rotativo en cookie `HttpOnly`;
- refresh token nunca en `localStorage` ni `sessionStorage`;
- logout real con revocación de sesión;
- protección CSRF para operaciones que dependen de cookies;
- rate limiting;
- HTTPS obligatorio en producción;
- CORS restrictivo;
- ownership estricto.

Base:

```text
/api/v1
```

---

## 2. Convenciones

### Access token

- JWT firmado.
- Duración objetivo: 10–15 minutos.
- Se devuelve al frontend en el cuerpo de la respuesta.
- El frontend lo conserva únicamente en memoria.
- Se envía en:

```http
Authorization: Bearer <access_token>
```

Claims mínimas:

```json
{
  "sub": "1",
  "sid": "session-id",
  "type": "access",
  "iat": 0,
  "exp": 0
}
```

No incluir información sensible innecesaria.

### Refresh token

Token opaco de alta entropía.

Formato recomendado:

```text
<session_id>.<random_secret>
```

La base de datos guarda únicamente el hash de `random_secret`.

Esto permite:
- localizar la sesión por `session_id`;
- verificar el secreto mediante hash;
- rotar el secreto;
- detectar presentación de un secreto antiguo/incorrecto para una sesión existente y revocar la sesión.

Cookie:

```text
Name=cognova_refresh
HttpOnly=true
Secure=true          # producción
SameSite=Lax
Path=/api/v1/auth
```

En desarrollo local `Secure` puede desactivarse exclusivamente mediante configuración de entorno.

### CSRF

Cognova usa un token CSRF separado.

Cookie:

```text
Name=cognova_csrf
HttpOnly=false
Secure=true          # producción
SameSite=Lax
Path=/api/v1/auth
```

El frontend lee esta cookie y la refleja en:

```http
X-CSRF-Token: <csrf_token>
```

El backend valida:
1. cookie CSRF presente;
2. header presente;
3. igualdad segura;
4. hash asociado a la sesión cuando corresponda.

El token CSRF no es una credencial de autenticación.

---

## 3. Registro

### POST `/api/v1/auth/register`

Request:

```json
{
  "name": "Sara",
  "email": "sara@example.com",
  "password": "Example123!",
  "degree_program": "Ingeniería de Software",
  "semester": 4,
  "academic_goal": "Mejorar mi constancia"
}
```

Reglas:

- `name`: requerido, no solo espacios;
- `email`: requerido, válido, normalizado, único case-insensitive;
- `password`: requerido, mínimo 8 caracteres, admitir contraseñas largas;
- `degree_program`: requerido, no solo espacios;
- `semester`: entero positivo;
- `academic_goal`: requerido, no solo espacios;
- rechazar campos extra si el esquema público no los permite.

Response `201 Created`:

```json
{
  "user": {
    "id": 1,
    "name": "Sara",
    "email": "sara@example.com",
    "degree_program": "Ingeniería de Software",
    "semester": 4,
    "academic_goal": "Mejorar mi constancia"
  },
  "access_token": "short_lived_access_token",
  "token_type": "bearer"
}
```

Además:
- crea `AuthSession`;
- establece `cognova_refresh`;
- establece/rota `cognova_csrf`.

Errores:
- `409 EMAIL_ALREADY_REGISTERED`
- `422 VALIDATION_ERROR`
- `429 TOO_MANY_REQUESTS`

---

## 4. Login

### POST `/api/v1/auth/login`

Request:

```json
{
  "email": "sara@example.com",
  "password": "Example123!"
}
```

Response `200 OK`: mismo `AuthResponse` del registro.

Además:
- crea una nueva `AuthSession`;
- establece refresh cookie;
- establece CSRF cookie.

Error de credenciales:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Correo o contraseña incorrectos."
  }
}
```

No indicar cuál de los dos campos falló.

Errores:
- `401 INVALID_CREDENTIALS`
- `422 VALIDATION_ERROR`
- `429 TOO_MANY_REQUESTS`

---

## 5. Usuario autenticado

### GET `/api/v1/auth/me`

Requiere access token Bearer.

Validar:
- firma;
- expiración;
- `type=access`;
- `sub`;
- `sid`;
- sesión existente;
- sesión no revocada;
- sesión no expirada.

Response `200 OK`:

```json
{
  "id": 1,
  "name": "Sara",
  "email": "sara@example.com",
  "degree_program": "Ingeniería de Software",
  "semester": 4,
  "academic_goal": "Mejorar mi constancia"
}
```

Errores:
- `401 INVALID_OR_EXPIRED_TOKEN`
- `401 SESSION_REVOKED`

---

## 6. Renovación

### POST `/api/v1/auth/refresh`

No acepta refresh token por JSON.

El navegador envía `cognova_refresh` automáticamente y el frontend envía `X-CSRF-Token`.

Proceso:

1. leer cookie;
2. extraer `session_id` y secreto;
3. obtener `AuthSession`;
4. validar que no esté revocada ni expirada;
5. validar CSRF;
6. comprobar hash del secreto;
7. si el secreto no coincide para una sesión existente, revocar esa sesión;
8. generar nuevo secreto de refresh;
9. reemplazar su hash;
10. rotar CSRF;
11. actualizar `last_used_at`;
12. emitir nuevo access token;
13. reemplazar cookies.

Response `200 OK`:

```json
{
  "access_token": "new_access_token",
  "token_type": "bearer"
}
```

Errores:
- `401 INVALID_REFRESH_TOKEN`
- `401 SESSION_REVOKED`
- `403 CSRF_VALIDATION_FAILED`
- `429 TOO_MANY_REQUESTS`

---

## 7. Logout

### POST `/api/v1/auth/logout`

Requiere:
- refresh cookie;
- `X-CSRF-Token`.

Proceso:
- revocar `AuthSession`;
- eliminar refresh cookie;
- eliminar CSRF cookie.

Response:

```text
204 No Content
```

El frontend elimina el access token de memoria.

Logout debe ser idempotente desde la perspectiva del usuario.

---

## 8. Sesiones activas

### GET `/api/v1/auth/sessions`

Requiere access token.

Devuelve únicamente sesiones del usuario autenticado.

Ejemplo:

```json
[
  {
    "id": "session-id",
    "created_at": "2026-10-05T10:00:00-05:00",
    "last_used_at": "2026-10-05T10:30:00-05:00",
    "expires_at": "2026-11-04T10:00:00-05:00",
    "current": true
  }
]
```

Nunca devolver:
- refresh token;
- refresh hash;
- CSRF hash;
- password hash.

### DELETE `/api/v1/auth/sessions/{session_id}`

Requiere access token.

Solo puede revocar una sesión perteneciente al usuario autenticado.

Si se revoca la sesión actual:
- revocar;
- limpiar cookies si corresponden a esa sesión;
- frontend debe cerrar sesión.

Errores:
- `404 SESSION_NOT_FOUND`
- `403 FORBIDDEN`

---

## 9. Restauración de sesión

Al cargar o recargar la aplicación:

```text
Frontend inicia sin access token
        ↓
lee cognova_csrf
        ↓
POST /auth/refresh + X-CSRF-Token
        ↓
nuevo access token en memoria
        ↓
GET /auth/me
        ↓
sesión restaurada
```

Si refresh falla:
- limpiar estado autenticado;
- no entrar en bucle;
- mostrar login.

---

## 10. Manejo de 401 en frontend

Cuando una petición protegida recibe `401` por access token expirado:

1. ejecutar como máximo un refresh coordinado;
2. si varias peticiones fallan simultáneamente, compartir el mismo refresh pendiente;
3. actualizar access token en memoria;
4. repetir una sola vez las peticiones originales;
5. si refresh falla, cerrar sesión;
6. nunca crear bucles infinitos.

---

## 11. Contraseñas

- Argon2id.
- Nunca almacenar contraseña en texto plano.
- Nunca registrar contraseña en logs.
- Nunca devolver `password_hash`.
- Soportar rehash cuando cambien parámetros recomendados.
- Comparación segura.

---

## 12. Rate limiting

Aplicar al menos a:

```text
POST /auth/register
POST /auth/login
POST /auth/refresh
```

Debe:
- ser configurable por entorno;
- responder `429`;
- tener pruebas;
- evitar incluir datos sensibles en claves/logs.

Los endpoints de IA también tendrán límites propios.

---

## 13. CORS y cookies

Producción:
- lista explícita de orígenes permitidos;
- credenciales habilitadas solo para orígenes concretos;
- nunca `Access-Control-Allow-Origin: *` con credenciales.

Si frontend y backend se despliegan realmente cross-site y `SameSite=Lax` no funciona, la decisión deberá documentarse antes de cambiar a:

```text
SameSite=None
Secure=true
```

CSRF sigue siendo obligatorio.

---

## 14. Errores de autenticación

Formato:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Mensaje legible."
  }
}
```

Códigos:

```text
EMAIL_ALREADY_REGISTERED
INVALID_CREDENTIALS
INVALID_OR_EXPIRED_TOKEN
INVALID_REFRESH_TOKEN
SESSION_REVOKED
SESSION_NOT_FOUND
CSRF_VALIDATION_FAILED
VALIDATION_ERROR
TOO_MANY_REQUESTS
UNAUTHORIZED
FORBIDDEN
```

---

## 15. Variables de entorno

Ejemplo conceptual:

```env
JWT_SECRET=
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
CORS_ALLOWED_ORIGINS=
AUTH_RATE_LIMIT=
```

No guardar secretos reales en Git.

---

## 16. Regla de compatibilidad

Este documento reemplaza cualquier decisión anterior que indique:

- JWT persistido en `localStorage`;
- logout solo local;
- ausencia de refresh tokens;
- autenticación stateless sin sesiones revocables.

El código existente que siga ese modelo debe migrarse; no borrarse a ciegas.
