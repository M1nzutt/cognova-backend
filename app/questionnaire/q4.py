"""Approved q4 wording and stable option identifiers."""

QUESTION = {
    "id": "q4",
    "text": "¿Cuánto dura normalmente una sesión de estudio?",
    "selection": "single",
    "min_choices": 1,
    "max_choices": 1,
    "options": [
        {"id": "under_30_minutes", "label": "Menos de 30 min"},
        {"id": "30_60_minutes", "label": "30–60 min"},
        {"id": "one_two_hours", "label": "1–2 horas"},
        {"id": "over_two_hours", "label": "Más de 2 horas"},
        {"id": "varies", "label": "Varía mucho"},
    ],
}
