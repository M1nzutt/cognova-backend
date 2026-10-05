# Cognova — Decisiones Congeladas

- Nombre: Cognova.
- Backend: Python + FastAPI.
- Frontend: React + TypeScript + Vite.
- DB: PostgreSQL.
- Dos repositorios; no monolito.
- POO obligatoria.
- Una clase relevante por archivo.
- Interfaz en español; código en inglés.
- Nivel técnico intermedio, bien organizado.
- Multiusuario.
- Perfil: nombre, carrera, semestre, objetivo académico.
- Materias personalizables.
- Actividad genérica con `type`.
- Prioridades manuales y deadlines.
- Calendario visual.
- Temporizador integrado.
- Motivos predefinidos + personalizados.
- Cuestionario obligatorio de 10 preguntas.
- IA como acompañante académico, no chatbot genérico.
- IA automática con evidencia suficiente y manual bajo demanda.
- Umbral mínimo: 5 sesiones.
- Retos: IA propone, usuario acepta/rechaza; no se editan.
- Gamificación: solo racha.
- Grafo: dependencias académicas.
- Sin pantalla especial para estructuras.
- Diseño: Notion + pastel + detalles cósmicos.
- Tema claro y oscuro.
- Seed demo obligatorio.
- Aplicación desplegada y funcional con IA real.

## Autenticación — 2026-10-05
- AUTH_CONTRACT.md define registro, login y usuario autenticado; prevalece sobre
  el listado abreviado de rutas de API_CONTRACT.md.
- IDs de usuario enteros generados por PostgreSQL; email normalizado a minúsculas
  en registro/login e índice único sobre lower(email) para evitar duplicados.
- Contraseñas con Argon2id (equivalente seguro permitido por el contrato), sin
  recortes ni cambios de espacios. JWT HS256 con secreto aleatorio de al menos
  32 bytes, expiración configurable y claims sub, email, exp.
- Los campos de texto obligatorios del registro no aceptan solo espacios;
  semester acepta únicamente enteros positivos. No se aceptan campos adicionales.
- /auth/me identifica al usuario por el sub del JWT validado y consulta su fila;
  no acepta un ID del cliente como autorización. No hay logout ni refresh token.
- Alembic administra el esquema; la aplicación no ejecuta create_all al arrancar.
