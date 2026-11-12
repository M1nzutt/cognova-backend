# Analytics académico — contrato API v1

Analytics es una vista autenticada, de solo lectura y calculada desde datos del
usuario. PostgreSQL conserva la fuente de verdad. Las estructuras en memoria se
construyen por solicitud con filas filtradas por el usuario y no se comparten ni
persisten. Analytics no crea eventos ni presenta correlaciones como causas.

## Rutas

- `GET /api/v1/analytics/overview`: resumen descriptivo de toda la historia.
- `GET /api/v1/analytics/study-time`: tiempo registrado dentro de un rango y sus
  buckets diarios, semanales o mensuales.
- `GET /api/v1/analytics/timeline`: eventos persistidos y fechas planificadas en
  un rango cronológico paginado. `AcademicArchive` indexa el historial y
  `BalancedTimeline` las fechas planificadas; sus recorridos se fusionan por orden.
- `GET /api/v1/analytics/search`: prefijo sobre Materias, Actividades, Planes y
  Retos propios.

No se implementan las rutas conceptuales antiguas `summary`, `by-time-of-day`,
`by-duration` ni `by-subject`; fueron sustituidas antes de tener implementación
pública por estos DTOs de Analytics.

Las cuatro rutas requieren Bearer válido y onboarding completo. Devuelven
`Cache-Control: no-store`; no reciben `user_id`, datos académicos ni payloads. Los
parámetros de query son estrictos: campos desconocidos dan 422.

## Overview

`GET /analytics/overview` no acepta filtros ni cursor. Cuenta todos los registros
actuales propios y devuelve:

- `total_studied_seconds` y `total_studied_minutes`, decimales con seis posiciones;
- `finished_sessions`: lifecycle `finished`, incluidos los cuatro resultados;
- `completed_sessions`, `partial_sessions`, `postponed_sessions` y
  `cancelled_sessions`, por resultado;
- `subjects_with_activity`: materias referenciadas por al menos una Actividad o
  Sesión propia;
- `completed_activities`, `pending_activities` e `in_progress_activities`;
- `active_plans`, `completed_plans`, `completed_challenges` y `failed_challenges`.

`pending_activities` significa status exactamente `pending`. Las métricas de
estado son snapshots actuales; no afirman cuándo cambió un estado. `total_studied`
se obtiene de `study_sessions.actual_duration`; los intervalos abiertos no se
suman hasta que Backend los cierre.

## Tiempo estudiado

`GET /analytics/study-time` requiere:

- `from`, `to`: ISO 8601 con offset explícito; no se acepta fecha sola ni datetime
  ingenuo. El intervalo es semiabierto `[from,to)`, `from < to` y máximo 366 días
  transcurridos.
- `granularity`: `day`, `week` o `month`; default `day`. Semana inicia lunes y
  mes usa límites calendario.
- `timezone`: nombre IANA; default `UTC`. Es explícito y no se infiere de la zona
  del servidor. Ejemplos: `America/Bogota`, `Europe/Madrid`.

Cada bucket devuelve límites ISO 8601 en la zona indicada, recortados al rango
solicitado. Los segundos son tiempo transcurrido real entre instantes; días de
cambio horario pueden durar 23 o 25 horas. Se consideran únicamente porciones
cerradas de `study_session_intervals` que se superponen con `[from,to)`. Un
intervalo que cruza el límite se recorta con precisión de microsegundos. Las
sesiones se cuentan distintas por ID dentro del rango y por materia; una Sesión con
varios intervalos cuenta una vez. Los buckets vacíos se devuelven con cero.

Respuesta `200`:

```json
{
  "from": "2030-01-01T00:00:00-05:00",
  "to": "2030-01-08T00:00:00-05:00",
  "timezone": "America/Bogota",
  "granularity": "day",
  "total_seconds": "10800.000000",
  "total_minutes": "180.000000",
  "sessions_count": 3,
  "by_subject": [
    {"subject_id": 4, "name": "Física", "seconds": "7200.000000", "minutes": "120.000000", "sessions_count": 2}
  ],
  "buckets": [
    {"from": "2030-01-01T00:00:00-05:00", "to": "2030-01-02T00:00:00-05:00", "seconds": "3600.000000", "minutes": "60.000000"}
  ]
}
```

`StudyRangeInsights` es un índice de segmentos ponderados por duración. El
servicio obtiene intervalos cerrados propios que se solapan con el rango; el índice
se destruye al terminar la solicitud. La duración usa consultas de suma O(log S)
por materia; el conteo de IDs de sesión distintos recorre O(S) intervalos.

## Timeline y archivo

`GET /analytics/timeline` requiere `from` y `to` con las reglas del rango anterior.
Admite `category` opcional (`activity`, `study_session`, `decision`, `plan`,
`challenge`), `limit` entre 1 y 100 (default 50) y `cursor` opaco opcional. Responde
`{items, next_cursor}`; no devuelve `total_count`.

Eventos admitidos y su instante autoritativo:

- Actividad creada (`activities.created_at`) y deadline vigente (`deadline`, tipo
  planificado); cambios de deadline (`activity_deadline_events.occurred_at` y su
  par de fechas).
- Sesión planificada (`planned_start_at`); inicio/cierre de ejecución desde cada
  `study_session_intervals.started_at` y `ended_at` presente.
- Plan creado (`study_plans.created_at`) y decisión
  (`study_plan_decisions.created_at`).
- Reto creado (`study_challenges.created_at`).

No se generan eventos de transición de status para Actividades, Planes o Retos:
las tablas no conservan ese historial. Tampoco se convierten deadlines ni horas
planificadas en afirmaciones de ejecución. Las decisiones exponen acción y
`field_path`, nunca `proposed_value`, `chosen_value`, snapshots IA ni JSON interno.
Las etiquetas de recursos provienen de filas propias y no contienen `user_id`.

Orden ascendente total: `occurred_at` UTC, categoría (`activity`,
`study_session`, `decision`, `plan`, `challenge`), ID del recurso, ID de ocurrencia
y tipo de ocurrencia. Empates siempre producen el mismo orden. `event_id` identifica
la ocurrencia como combinación de tipo e IDs; no es un ID global de recurso. El
cursor exclusivo contiene la clave de orden y una huella de rango/filtros; no es
credencial. Conservar rango y filtros al continuar. Sin snapshot entre páginas:
cambios en fechas fuente pueden mover un elemento; reiniciar el recorrido.
Un cursor mal formado o reutilizado con otros filtros da 422.

`AcademicArchive` es el índice B-tree en memoria de eventos históricos inmutables
(cambios de deadline, intervalos y decisiones); ofrece búsqueda/rango ordenado y
página sobre filas ya leídas. Su fanout reduce niveles de recorrido para un archivo
ordenado con inserciones, aun cuando los nodos se mantienen en memoria.
`BalancedTimeline` mantiene las fechas planificadas/recursos actuales y permite
insertar sin reconstruir una lista ordenada. El servicio fusiona ambos recorridos.
No hay tabla ni índice SQL nuevo.

## Búsqueda

`GET /analytics/search` requiere `prefix` de 1–64 caracteres después de recortar
espacios, acepta `type` opcional (`subject`, `activity`, `study_plan`,
`study_challenge`), `limit` 1–50 (default 20) y `cursor` opcional. Responde
`{items, next_cursor}`; vacío es `200` con lista vacía. El resultado incluye tipo,
ID, título y solo relaciones propias necesarias para navegar.

El prefijo y títulos se normalizan con Unicode `casefold`, descomposición NFD y
eliminación de marcas combinantes. Por ello `fisica` encuentra `Física` sin
distinguir mayúsculas ni tildes; no se transliteran otros alfabetos. Se deduplica
por `(type,id)`. Orden estable: clave normalizada, tipo e ID. El cursor queda
vinculado al prefijo/tipo. `AcademicFinder` indexa nombres en un Trie; el servicio
carga recursos filtrados por el usuario y construye el índice por request.

## Directorio y seguridad

`ResourceDirectory` indexa por `(type,id)` materias, Actividades, Sesiones, Planes
y Retos para resolver relaciones de eventos sin consultas N+1. La búsqueda usa el
mismo directorio para construir el Trie. Ninguna estructura es global ni comparte
datos entre solicitudes/usuarios.

Errores: `401` Bearer requerido/inválido, `403 ONBOARDING_REQUIRED`, `422
VALIDATION_ERROR` por filtros/rango/cursor, `503 SERVICE_UNAVAILABLE` por fallo de
PostgreSQL. No hay 404 para una Materia o recurso ajeno usado en un filtro; no se
consulta su existencia. Las consultas usan únicamente `user.id` autenticado en
cada fuente, incluidas tablas de historial enlazadas a la tabla propietaria.
Analytics solo usa SELECT.

## Límites y complejidad

Rangos de tiempo máximo 366 días; timeline hasta 100 eventos por página y búsqueda
hasta 50 recursos por página. Se consultan solo filas del usuario autenticado y,
para tiempo/timeline, solo las que se solapan con el rango. No hay cache global.
Construir el segment tree cuesta `O(S log S)` y usa `O(S)` espacio; una consulta
de duración cuesta `O(P log S)` y el conteo de sesiones distintas agrega `O(S)`.
Construir el B-tree y el árbol rojo-negro cuesta `O(E log E)`; tras construirlos,
el recorrido de página cuesta `O(log E + k)`. El directorio hash cuesta `O(R)`
al construir, `O(1)` esperado por acceso y `O(R)` peor caso con colisiones. Trie:
`O(L)` para ubicar prefijo de longitud `L`, más recolección y ordenamiento de `M`
coincidencias (`O(M log M)`). `R`, `E`, `S` y `M` son filas/recursos propios de
esa solicitud; ninguna estructura sobrevive al request. Los límites temporales y
paginación limitan la respuesta; no imponen un máximo artificial a la historia.
