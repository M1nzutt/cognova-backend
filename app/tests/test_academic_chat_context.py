import json

from app.models.academic_chat import AcademicMessage
from app.services.academic_chat_service import (
    MAX_HISTORY_CHARS,
    MAX_MODEL_CONTEXT_BYTES,
    AcademicChatService,
)


def test_model_context_is_bounded_and_retains_only_recent_history():
    activities = [
        {"id": index, "title": f"Actividad {index}", "status": "pending"}
        for index in range(1, 201)
    ]
    source = {
        "evidence_catalog": {
            f"activity:{index}": f"Evidencia de actividad {index}."
            for index in range(1, 201)
        },
        "questionnaire_answers": {"large": "dato " * 8000},
        "subjects": [{"id": 1, "name": "Física"}],
        "activities": activities,
        "sessions": [],
        "previous_plans": [],
        "previous_challenges": [],
        "user_decisions": [],
        "finished_valid_sessions": 0,
        "nearby_schedule": [],
    }
    messages = [
        AcademicMessage(role="user", content=f"Pregunta {index}")
        for index in reversed(range(12))
    ]

    result = AcademicChatService._build_context(
        json.dumps(source, ensure_ascii=False), messages
    )

    assert len(result.encode("utf-8")) <= MAX_MODEL_CONTEXT_BYTES
    context = json.loads(result)
    history = context["recent_conversation"]
    assert sum(len(item["content"]) for item in history) <= MAX_HISTORY_CHARS
    assert history[-1]["content"] == "Pregunta 11"
    assert len(context["academic_context"]["activities"]) <= 24
