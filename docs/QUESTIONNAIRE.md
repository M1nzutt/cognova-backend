# Cognova — Cuestionario / percepción inicial, catálogo 1

Las preguntas y etiquetas siguientes están aprobadas. IDs ASCII estables de backend;
no traducir IDs ni reemplazar etiquetas. Las diez preguntas son obligatorias.
Single: exactamente una selección. Multi: de una al máximo indicado, sin duplicados.
`other` solo existe en q1/q6/q7 y exige texto con trim, de 1 a 50 caracteres.
Sin `other` seleccionado, `other_text` debe ser null u omitido.

## q1: ¿Cuál es tu objetivo académico principal?

single: exactamente 1.

| ID | Etiqueta exacta |
| --- | --- |
| organize_time | Organizar mejor mi tiempo |
| be_consistent | Ser más constante |
| complete_activities | Cumplir mejor mis actividades |
| prepare_assessments | Prepararme para evaluaciones |
| understand_subjects | Entender mejor mis materias |
| reduce_procrastination | Reducir la procrastinación |
| other | Otro |

## q2: ¿Cuántos días a la semana estudias fuera de clases?

single: exactamente 1.

| ID | Etiqueta exacta |
| --- | --- |
| almost_never | Casi nunca |
| one_two_days | 1–2 días |
| three_four_days | 3–4 días |
| five_six_days | 5–6 días |
| every_day | Todos los días |

## q3: ¿En qué momento del día estudias mejor?

single: exactamente 1.

| ID | Etiqueta exacta |
| --- | --- |
| morning | Mañana |
| afternoon | Tarde |
| night | Noche |
| depends | Depende |

## q4: ¿Cuánto dura normalmente una sesión de estudio?

single: exactamente 1.

| ID | Etiqueta exacta |
| --- | --- |
| under_30_minutes | Menos de 30 min |
| 30_60_minutes | 30–60 min |
| one_two_hours | 1–2 horas |
| over_two_hours | Más de 2 horas |
| varies | Varía mucho |

## q5: ¿Qué tan seguido cumples lo que planeas estudiar?

single: exactamente 1.

| ID | Etiqueta exacta |
| --- | --- |
| almost_never | Casi nunca |
| rarely | Pocas veces |
| sometimes | A veces |
| almost_always | Casi siempre |
| always | Siempre |

## q6: ¿Qué suele dificultarte estudiar?

multi: entre 1 y 3.

| ID | Etiqueta exacta |
| --- | --- |
| distractions | Distracciones |
| tiredness | Cansancio |
| lack_of_time | Falta de tiempo |
| lack_of_motivation | Falta de motivación |
| not_knowing_where_to_start | No saber por dónde empezar |
| too_many_activities | Demasiadas actividades |
| difficulty_with_subject | Dificultad con una materia |
| other | Otro |

## q7: ¿Cómo organizas tus actividades académicas?

multi: entre 1 y 2.

| ID | Etiqueta exacta |
| --- | --- |
| planner_calendar | Agenda o calendario |
| application | Aplicación |
| phone_notes | Notas en el celular |
| notebook | Cuaderno |
| memory | De memoria |
| only_urgent | Solo organizo lo urgente |
| no_method | No tengo un método |
| other | Otro |

## q8: ¿Cómo decides qué actividad hacer primero?

single: exactamente 1.

| ID | Etiqueta exacta |
| --- | --- |
| most_urgent | La más urgente |
| most_important | La más importante |
| hardest | La más difícil |
| quickest | La más rápida |
| by_subject | Según la materia |
| by_mood | Según mis ganas |
| no_criterion | No tengo un criterio |

## q9: ¿Qué haces cuando no cumples una sesión planeada?

single: exactamente 1.

| ID | Etiqueta exacta |
| --- | --- |
| reschedule | La reprogramo |
| later | La hago más tarde |
| partially | Hago solo una parte |
| cancel | La cancelo |
| leave_pending | La dejo pendiente |
| depends | Depende |

## q10: ¿Qué te gustaría entender mejor sobre tu forma de estudiar?

multi: entre 1 y 3.

| ID | Etiqueta exacta |
| --- | --- |
| best_times | Mis mejores horarios |
| consistency | Mi constancia |
| actual_study_time | Mi tiempo real de estudio |
| plan_completion | Si cumplo lo que planeo |
| neglected_subjects | Qué materias descuido más |
| why_postpone | Por qué aplazo actividades |
| time_distribution | Cómo distribuyo mi tiempo |
| helpful_habits | Qué hábitos me ayudan |

La percepción inicial es la revisión 1, inmutable. PUT agrega una nueva revisión
completa del catálogo 1; no sobrescribe respuestas anteriores. El objetivo
académico actual es q1, no un campo de registro/User. El archivo legacy de 0003
conserva la evidencia previa sin inventar las otras nueve respuestas.

DTO y rutas en [API_CONTRACT.md](API_CONTRACT.md). La IA observa, relaciona,
cuestiona y pregunta. El usuario interpreta y decide. No inferir patrones antes
de 5 sesiones válidas.
