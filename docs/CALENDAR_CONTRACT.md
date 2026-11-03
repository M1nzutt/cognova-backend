# Calendario — contrato API v1 ampliado y Live (2026-11-02)

Vista transversal, autenticada, de solo lectura y limitada a recursos propios. El
calendario no crea ni modifica recursos, no admite eventos libres, no duplica datos y
no tiene tablas, migraciones ni grants propios. Sus fuentes son Actividades (0005)
y Sesiones de Estudio (0006).

## Endpoint y filtros

`GET /api/v1/calendar`, Bearer y onboarding completo obligatorios; todas las
respuestas usan `Cache-Control: no-store`. Query estricta (`extra=forbid`):

- `deadline_from` y `deadline_to` obligatorios: ISO 8601 con zona; no fecha sola ni
  epoch. El rango es semiabierto `[from,to)`, `from < to`, máximo 366 días de tiempo
  transcurrido. Se compara contra `deadline` vigente de Actividades y
  `planned_start_at` de Sesiones. Frontend calcula límites de su zona y los envía
  con offset; no se infiere zona del servidor ni se agrupan días aquí.
- `type` opcional: `activity` o `study_session`. Omitirlo devuelve ambas fuentes.
- `subject_id` entero positivo int32 opcional, aplicable a ambas fuentes. Materia
  ajena o inexistente devuelve lista vacía, sin consultar su existencia.
- `status` y `priority` mantienen los valores y significado anteriores, aplicados
  solo a Actividades. Si se suministra cualquiera, las Sesiones no forman parte de
  los resultados. Combinarlos con `type=study_session` es inválido (422).
- `limit=50`, entre 1 y 100. Se lee como máximo `limit+1` elementos.
- Cursor exclusivo: `after_deadline`, `after_type` y `after_id`. La fecha es el
  instante cronológico del elemento (deadline de actividad o planned_start_at de
  sesión). En solicitudes nuevas los tres campos vienen juntos. Para compatibilidad,
  la pareja anterior `after_deadline` + `after_id` se acepta sin `after_type` y se
  interpreta como cursor de `activity`. El cursor debe caer dentro del rango y el
  ID debe ser positivo int32. No se exige que el recurso del cursor aún exista.
  Conservar rango y filtros al paginar.

Los filtros aplicables se combinan con AND. Todos los estados de ambas fuentes y
las materias archivadas se incluyen por defecto. Las respuestas vacías tienen
`items=[]` y `next_cursor=null`.

## Respuesta y orden

`200: {items:[CalendarItem], next_cursor: CalendarCursor|null}`. La identidad
pública es `(type,id)`; los IDs no son globales entre tipos. Un recurso original
produce como máximo un elemento. No se copia historial, user_id ni datos de otras
tablas que el cliente ya puede obtener desde sus endpoints propios.

`CalendarActivityItem` conserva sin cambios el DTO anterior: `id`, `type` literal
`activity`, `title`, `subject_id`, `deadline`, `original_deadline`, `priority`,
`status` y `estimated_duration`. Su posición usa el `deadline` vigente; los cambios
de fecha no crean eventos adicionales.

`CalendarStudySessionItem` expone `id`, `type` literal `study_session`, `subject_id`,
`activity_id` nullable, `planned_start_at`, `planned_duration`, `lifecycle`, `result`
nullable, `start_at` nullable y `end_at` nullable. `lifecycle` conserva los estados
`planned`, `running`, `paused` y `finished`; `result` usa los resultados definidos en
`STUDY_SESSIONS_CONTRACT`. Las fechas son ISO 8601 con zona. La posición usa siempre
`planned_start_at`, incluso si la sesión ya se inició o terminó.

Orden total ascendente: instante del evento, rango de tipo y luego ID. Para empates
temporales, `activity` precede a `study_session`; dentro de cada tipo se ordena por
ID ascendente. `next_cursor` conserva `after_deadline` y `after_id` e incluye
`after_type` para definir completamente el elemento de continuación. La forma antigua
de cursor sigue aceptándose para Actividades. Se conserva rango y filtros durante la
paginación. No hay snapshot entre páginas: si cambia la fecha de un recurso durante
el recorrido, puede moverse de página; refrescar el rango. No se devuelve
`total_count`.

Ejemplo:

```text
GET /api/v1/calendar?deadline_from=2030-01-01T00:00:00Z&deadline_to=2030-02-01T00:00:00Z&limit=50
```

Copiar todos los campos de `next_cursor` a la siguiente petición junto con los
filtros originales. Codificar el signo `+` de offsets positivos como `%2B`.

## Escrituras, seguridad y errores

Calendario solo expone GET; POST/PUT/PATCH/DELETE responden 405. No hay endpoint de
detalle duplicado. El servicio ejecuta SELECT con ownership por `user_id` derivado
del Bearer; no recibe `user_id` del cliente, no toca recursos ni historial, no toma
locks de escritura ni confirma transacciones. No se consulta la existencia de
materias ajenas para filtros.

401 auth, 403 `ONBOARDING_REQUIRED`, 422 `VALIDATION_ERROR` (query inválida), 503
`SERVICE_UNAVAILABLE` (DB); formato global `{error:{code,message}}` sin SQL. Una
consulta sin resultados no produce 404. CSRF y auth existentes no cambian.

## Estado

La ampliación es transversal y de solo lectura sobre las tablas ya existentes; no
requiere cambios en Database. Implementación, pruebas, integración y evidencia de
release se registran en `PROJECT_STATE.md`, `DEPLOYMENT.md` e
`INTEGRATION_VALIDATION.md`.

Release cerrado: merge `4735a697aed69f66f3055c902a00507b66a556e0`, Render Live
deploy `dep-dbkjld7lk1mc73duk6jg`, DB `0006_study_sessions` sin cambios. CI de rama
`41560379932` y de merge `41560869679` pasó; smoke autenticado mixto aprobado. Frontend
puede continuar con este contrato.
