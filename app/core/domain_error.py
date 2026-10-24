class DomainError(Exception):
    _errors = {
        "ACTIVITY_NOT_FOUND": (404, "Actividad no encontrada."),
        "ACTIVITY_TRANSITION_CONFLICT": (
            409,
            "Reabre la actividad como pendiente antes de cambiar a ese estado.",
        ),
        "ACTIVITY_STATE_CONFLICT": (
            409,
            "El estado cambió; consulta la actividad e intenta de nuevo.",
        ),
        "ACTIVITY_DEADLINE_CONFLICT": (
            409,
            "La fecha cambió; consulta la actividad e intenta de nuevo.",
        ),
        "ACTIVITY_HAS_DEPENDENCIES": (
            409,
            "No puedes eliminar una actividad con historial o registros relacionados.",
        ),
        "ACTIVITY_WRITE_CONFLICT": (
            409,
            "La actividad cambió durante la operación; consulta e intenta de nuevo.",
        ),
        "SUBJECT_NOT_FOUND": (404, "Materia no encontrada."),
        "SUBJECT_NAME_CONFLICT": (409, "Ya existe una materia con ese nombre."),
        "SUBJECT_ACTIVE_LIMIT": (409, "Puedes tener máximo cinco materias activas."),
        "SUBJECT_REACTIVATION_LIMIT": (
            409,
            "Archiva otra materia antes de reactivar esta.",
        ),
        "SUBJECT_HAS_DEPENDENCIES": (
            409,
            "No puedes eliminar una materia con registros relacionados.",
        ),
        "SUBJECT_WRITE_CONFLICT": (
            409,
            "La materia cambió durante la operación; consulta e intenta de nuevo.",
        ),
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
