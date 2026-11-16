"""Fictional TurnoClaro semester. Dates here are plans, never execution history."""

from datetime import date, datetime, time, timedelta, timezone

VERSION = 1
IDENTITY = {"name": "Lucia Torres Demo", "email": "demo.software@example.com"}
SUBJECTS = [
    ("req", "Req. de Software", "hard"),
    ("arq", "Arquitectura SW", "hard"),
    ("bd", "Bases de Datos", "medium"),
    ("qa", "Calidad y Pruebas", "medium"),
    ("agil", "Gestión Ágil", "easy"),
]
TOPICS = {
    "req": ["Entrevistas", "Historias de usuario", "Criterios de aceptación",
            "Prototipo de reservas", "Validación del alcance", "Entrega de requisitos"],
    "arq": ["Contexto del sistema", "Diagramas de componentes", "Contrato REST",
            "Diseño de servicios", "Revisión de seguridad", "Integración de módulos"],
    "bd": ["Modelo de entidades", "Normalización", "Consultas de reservas",
           "Índices y rendimiento", "Transacciones", "Entrega de persistencia"],
    "qa": ["Plan de calidad", "Casos de prueba", "Pruebas unitarias",
           "Pruebas de integración", "Regresión de reservas", "Informe de calidad"],
    "agil": ["Backlog inicial", "Estimación de historias", "Revisión del sprint",
             "Ajuste de prioridades", "Retrospectiva", "Preparación de entrega"],
}


def instant(reference: date, offset: int, hour: int = 18) -> str:
    return datetime.combine(
        reference + timedelta(days=offset), time(hour), timezone.utc
    ).isoformat()


def activities(reference: date) -> list[dict]:
    result = []
    for week in range(6):
        for index, (key, _, _) in enumerate(SUBJECTS):
            result.append({
                "key": f"activity-{key}-w{week + 1}",
                "subject_key": key,
                "week": week,
                "body": {
                    "title": f"S{week + 1} {TOPICS[key][week]}",
                    "deadline": instant(reference, -35 + week * 7 + index),
                    "priority": ("low", "medium", "high")[(week + index) % 3],
                    "status": "pending",
                    "estimated_duration": [45, 60, 90][index % 3],
                    "notes": (
                        f"TurnoClaro demo v{VERSION}; semana {week + 1}. "
                        "Planificación ficticia; cambios y ejecución registrados "
                        "con fecha real al preparar o utilizar la cuenta."
                    ),
                },
            })
    return result


def sessions(reference: date) -> list[dict]:
    result = []
    for week in range(6):
        for index, (key, _, _) in enumerate(SUBJECTS):
            result.append({
                "key": f"session-{key}-w{week + 1}",
                "activity_key": f"activity-{key}-w{week + 1}",
                "subject_key": key,
                "body": {
                    "planned_start_at": instant(reference, -36 + week * 7 + index, 15),
                    "planned_duration": [45, 60, 75][index % 3],
                },
            })
    for index, (key, _, _) in enumerate(SUBJECTS):
        result.append({
            "key": f"rehearsal-{key}",
            "activity_key": f"activity-{key}-w6",
            "subject_key": key,
            "body": {
                "planned_start_at": instant(reference, 0, 9 + index),
                "planned_duration": 10,
            },
        })
    result.append({
        "key": "future-timer",
        "activity_key": "activity-arq-w6",
        "subject_key": "arq",
        "body": {"planned_start_at": instant(reference, 6, 16),
                 "planned_duration": 45},
    })
    return result
