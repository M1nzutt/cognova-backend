# Cognova — Modelo de Datos

## Entidades
- User: id, name, email, password_hash, degree_program, semester, academic_goal, created_at
- Questionnaire: id, user_id, answers_json, created_at, updated_at
- Subject: id, user_id, name, description, color, created_at
- Goal: id, user_id, subject_id?, title, description, target_date, status
- AcademicActivity: id, user_id, subject_id, goal_id?, title, description, type, priority, deadline, status
- StudySession: id, user_id, subject_id, activity_id?, planned_start, planned_minutes, actual_minutes, result, reason, custom_reason?, context_note?, started_at?, finished_at?
- AIConversation: id, user_id, created_at, updated_at
- AIMessage: id, conversation_id, role, content, metadata_json, created_at
- AIObservation: id, user_id, message, evidence_json, sample_size, created_at, user_feedback?
- Reflection: id, user_id, observation_id?, message_id?, text, created_at
- Challenge: id, user_id, title, description, evidence_json, status, start_date, end_date, result_note?
- StudyStreak: id, user_id, current_streak, best_streak, last_valid_study_date
