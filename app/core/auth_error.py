class AuthError(Exception):
    """Known authentication failures with contract-defined public messages."""

    _errors = {
        "EMAIL_ALREADY_REGISTERED": (409, "El correo ya está registrado."),
        "INVALID_CREDENTIALS": (401, "Correo o contraseña incorrectos."),
        "INVALID_OR_EXPIRED_TOKEN": (
            401, "La sesión expiró o el token no es válido."
        ),
    }

    def __init__(self, code: str) -> None:
        self.code = code
        self.status_code, self.message = self._errors[code]
        super().__init__(self.message)
