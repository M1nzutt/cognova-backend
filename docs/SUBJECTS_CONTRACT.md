# Materias — contrato 2026-10-18

Base /api/v1. Bearer y onboarding completo obligatorios en todas las rutas,
incluido catálogo; no-store y errores globales existentes. No cambia auth.
DB fija c3394c38c55a8cd466d10f02fe7c80d7c1e1980f, revisión 0004_subjects.

## DTOs y catálogo

SubjectWrite: {name, difficulty, color_base, color_shade}, todos requeridos,
extra=forbid. name se normaliza NFC y strip, 1–20 caracteres, sin controles;
unicidad por usuario mediante comparación Unicode NFC + casefold en Backend,
incluyendo archivadas; el índice lower(name) PostgreSQL refuerza la regla según
la collation DB. Casefold también iguala ß/SS; se conserva el nombre de presentación.
difficulty: easy (Fácil), medium (Media), hard (Difícil).
color_base: blue, violet, pink, rose, orange, amber, green, teal, cyan, slate.
color_shade: entero estricto 100, 200, 300, 400 o 500; todas las combinaciones
base/shade son válidas. Catálogo versión 1; tokens, no códigos CSS libres.

SubjectCreate añade status opcional active (Activa, default) o archived (Archivada).
PUT usa SubjectWrite completo y no altera estado. Nunca aceptar user_id,
active_slot, timestamps ni id en cuerpos.

SubjectResponse: {id,name,status,difficulty,color_base,color_shade,created_at,
updated_at}; timestamps ISO 8601. No expone user_id ni active_slot.

## Endpoints

| Método/ruta | Request | Respuesta |
| --- | --- | --- |
| GET /subjects/catalog | ninguno | 200 {version:1,color_bases:[...],color_shades:[100,200,300,400,500]} |
| POST /subjects | SubjectCreate | 201 SubjectResponse |
| GET /subjects | status=active (default), archived o all; limit=20 (1–100), after_id positivo opcional | 200 {items:[SubjectResponse],next_after_id:int o null} |
| GET /subjects/{id} | ID positivo int32 | 200 SubjectResponse |
| PUT /subjects/{id} | SubjectWrite completo | 200 SubjectResponse |
| POST /subjects/{id}/archive | sin cuerpo | 200 SubjectResponse |
| POST /subjects/{id}/reactivate | sin cuerpo | 200 SubjectResponse |
| DELETE /subjects/{id}?confirm=true | confirm requerido, literal true | 204 sin cuerpo |

Listado por id ASC con cursor exclusivo; conservar filtro al paginar.
No promete snapshot entre páginas. Archivo/reactivación idempotentes: repetir
el estado actual no cambia updated_at ni consume otra posición.
DELETE es irreversible; Frontend debe solicitar confirmación al usuario. No
borra dependencias ni historia por cascada. Una segunda eliminación da 404.
No se incorpora auditoría de cambios ni actividades en esta entrega.

## Errores

Formato {error:{code,message}}; 422 VALIDATION_ERROR para DTO/query/path inválidos.
401 conserva auth; 403 ONBOARDING_REQUIRED si onboarding incompleto.
404 SUBJECT_NOT_FOUND tanto inexistente como ajena (no enumeración).
409 SUBJECT_NAME_CONFLICT: nombre reservado por otra materia del usuario.
409 SUBJECT_ACTIVE_LIMIT: crear una sexta activa.
409 SUBJECT_REACTIVATION_LIMIT: reactivar sin posición libre.
409 SUBJECT_HAS_DEPENDENCIES: FK impide DELETE, sin perder ningún dato.
409 SUBJECT_WRITE_CONFLICT: agotados tres intentos por concurrencia; releer/reintentar.
503 SERVICE_UNAVAILABLE conserva manejo de fallos DB no recuperables.
Nunca devolver mensajes nativos PostgreSQL, SQL ni valores internos.

## Transacciones y reglas DB / Backend

El servicio termina la transacción de solo lectura de auth/onboarding y abre
una transacción explícita READ COMMITTED en cada intento, incluso si la sesión
heredó otro aislamiento; no debe recibir cambios pendientes de otros servicios.
Esto permite releer nombres/posiciones tras esperar un lock sin snapshots viejos.
Toda mutación bloquea primero users.id con SELECT FOR UPDATE y luego busca la
materia filtrada por user_id. Así se serializan crear/editar/archivar/reactivar/
eliminar por usuario y se mantiene el orden de bloqueos del cuestionario.
Asignar la menor posición libre 1–5 para active; archived usa NULL. El check y
UNIQUE(user_id,active_slot) de DB son garantía final, incluso ante SQL externo.

Backend compara nombres del usuario bajo lock usando NFC + casefold porque
lower() en collation C no iguala É/é. Esta comprobación Unicode complementa el
índice; uq_subjects_user_name_lower también se traduce a 409 ante escritores SQL.
La restricción de capacidad justifica leer posiciones para asignarlas,
no reemplaza la garantía física por count(*). Reintentar la transacción completa
tras rollback por slot UNIQUE, 40001 o 40P01, máximo tres intentos y pausa acotada.
Cada reintento relee propiedad, estado y posiciones; no reintentar errores de
conexión/commit ambiguo. Mantener id/user_id/created_at; updated_at solo al cambiar.

Runtime necesita SELECT/INSERT/UPDATE/DELETE sobre subjects, USAGE/SELECT sobre
subjects_id_seq y SELECT/UPDATE sobre users para locks; no TRUNCATE ni DDL.
El DELETE es una ampliación deliberada respecto al contrato inicial Database,
autorizada por este módulo y pendiente de grants por operación. Futuras FK a
subjects deben ser RESTRICT: no eludirlas ni borrar historial para liberar cupo.

## Integración y rollout

Frontend puede integrar este contrato y OpenAPI al completar las pruebas. La API
productiva no dispone de Materias hasta aplicar 0004 desde Database, revisar grants
y desplegar esta rama coordinadamente. Backend exige exactamente 0004 en readiness;
0003 debe dar 503. No merge/deploy ni DDL productivo desde esta tarea.
