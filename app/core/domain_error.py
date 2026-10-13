class DomainError(Exception):
    _errors = {
        "QUESTIONNAIRE_NOT_FOUND": (404, "Aún no has completado el cuestionario."),
        "QUESTIONNAIRE_ALREADY_EXISTS": (409, "El cuestionario inicial ya existe."),
        "QUESTIONNAIRE_VERSION_CONFLICT": (
            409,
            "El cuestionario cambió; consulta la versión actual.",
        ),
        "ONBOARDING_REQUIRED": (403, "Completa el onboarding para continuar."),
        "LEGACY_PROFILE_REMEDIATION_REQUIRED": (
            409,
            "Tu identidad histórica requiere revisión antes de actualizar el perfil.",
        ),
    }

    def __init__(self, code: str) -> None:
        self.code = code
        self.status_code, self.message = self._errors[code]
        super().__init__(self.message)
