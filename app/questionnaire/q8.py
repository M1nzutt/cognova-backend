"""Approved q8 wording and stable option identifiers."""

QUESTION = {
    "id": "q8",
    "text": "¿Cómo decides qué actividad hacer primero?",
    "selection": "single",
    "min_choices": 1,
    "max_choices": 1,
    "options": [
        {"id": "most_urgent", "label": "La más urgente"},
        {"id": "most_important", "label": "La más importante"},
        {"id": "hardest", "label": "La más difícil"},
        {"id": "quickest", "label": "La más rápida"},
        {"id": "by_subject", "label": "Según la materia"},
        {"id": "by_mood", "label": "Según mis ganas"},
        {"id": "no_criterion", "label": "No tengo un criterio"},
    ],
}
