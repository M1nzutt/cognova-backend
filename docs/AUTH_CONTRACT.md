# Cognova — Contrato de Autenticación

## Base

Todos los endpoints usan el prefijo:

```text
/api/v1
```

La autenticación usa JWT Bearer.

---

# 1. Registro

## Endpoint

```http
POST /api/v1/auth/register
```

## Request

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

## Reglas

- `name`: obligatorio.
- `email`: obligatorio, formato válido y único.
- `password`: obligatorio, mínimo 8 caracteres.
- `degree_program`: obligatorio.
- `semester`: obligatorio, entero positivo.
- `academic_goal`: obligatorio.

## Response — 201 Created

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
  "access_token": "jwt_token",
  "token_type": "bearer"
}
```

## Errores

### 409 Conflict

```json
{
  "error": {
    "code": "EMAIL_ALREADY_REGISTERED",
    "message": "El correo ya está registrado."
  }
}
```

### 422 Validation Error

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Hay datos inválidos en el formulario."
  }
}
```

---

# 2. Login

## Endpoint

```http
POST /api/v1/auth/login
```

## Request

```json
{
  "email": "sara@example.com",
  "password": "Example123!"
}
```

## Response — 200 OK

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
  "access_token": "jwt_token",
  "token_type": "bearer"
}
```

## Error — 401 Unauthorized

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Correo o contraseña incorrectos."
  }
}
```

---

# 3. Usuario autenticado

## Endpoint

```http
GET /api/v1/auth/me
```

## Header

```http
Authorization: Bearer <access_token>
```

## Response — 200 OK

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

## Error — 401 Unauthorized

```json
{
  "error": {
    "code": "INVALID_OR_EXPIRED_TOKEN",
    "message": "La sesión expiró o el token no es válido."
  }
}
```

---

# 4. Logout

El backend no mantiene sesiones persistentes.

El frontend elimina el token almacenado localmente.

No se requiere endpoint de logout en esta primera versión.

---

# 5. JWT

Configuración esperada:

```env
JWT_SECRET=
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
```

Claims mínimas:

```json
{
  "sub": "1",
  "email": "sara@example.com",
  "exp": 0
}
```

`sub` representa el ID del usuario.

---

# 6. Contraseña

El backend debe:

- recibir contraseña en texto plano únicamente durante registro/login;
- almacenarla hasheada;
- nunca devolver `password_hash`;
- nunca registrar contraseñas en logs;
- usar bcrypt o equivalente seguro.

---

# 7. Token en frontend

Para este proyecto académico:

- almacenar el access token en `localStorage`;
- enviarlo como `Authorization: Bearer <token>`;
- eliminarlo al cerrar sesión;
- eliminarlo si el backend responde 401 por token inválido/expirado.

No guardar contraseña.

---

# 8. Flujo de registro

```text
Usuario
  ↓
RegisterPage
  ↓
POST /auth/register
  ↓
Backend valida
  ↓
Crea usuario
  ↓
Genera JWT
  ↓
Frontend guarda token
  ↓
Usuario va al cuestionario inicial
```

---

# 9. Flujo de login

```text
Usuario
  ↓
LoginPage
  ↓
POST /auth/login
  ↓
Backend valida credenciales
  ↓
Genera JWT
  ↓
Frontend guarda token
  ↓
GET /auth/me opcional para restaurar sesión
  ↓
Dashboard
```

---

# 10. Flujo de sesión expirada

```text
Frontend llama endpoint protegido
  ↓
Backend responde 401
  ↓
Frontend elimina token
  ↓
Redirige a /login
  ↓
Muestra:
"Tu sesión expiró. Inicia sesión nuevamente."
```

---

# 11. Códigos de error de autenticación

```text
EMAIL_ALREADY_REGISTERED
INVALID_CREDENTIALS
INVALID_OR_EXPIRED_TOKEN
VALIDATION_ERROR
UNAUTHORIZED
```

---

# 12. Reglas para ambos agentes

## Backend

Debe implementar exactamente:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

## Frontend

Debe consumir exactamente esos endpoints.

No inventar:

```text
/auth/signin
/auth/signup
/users/login
/users/register
```

sin modificar antes el contrato compartido.
