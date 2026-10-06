class AuthError(Exception):
    """Known authentication failures with contract-defined public messages."""

    _errors = {
        "INVALID_REFRESH_TOKEN": (401, "El token de renovación no es válido."),
        "SESSION_REVOKED": (401, "La sesión ha sido revocada."),
        "SESSION_NOT_FOUND": (404, "La sesión no existe."),
        "CSRF_VALIDATION_FAILED": (403, "La validación CSRF falló."),
        "TOO_MANY_REQUESTS": (429, "Demasiadas solicitudes. Intenta más tarde."),
        "FORBIDDEN": (403, "No tienes permiso para realizar esta acción."),
        "EMAIL_ALREADY_REGISTERED": (409, "El correo ya está registrado."),
        "INVALID_CREDENTIALS": (401, "Correo o contraseña incorrectos."),
        "INVALID_OR_EXPIRED_TOKEN": (401, "La sesión expiró o el token no es válido."),
    }

    def __init__(self, code: str) -> None:
        self.code = code
        self.status_code, self.message = self._errors[code]
        super().__init__(self.message)
