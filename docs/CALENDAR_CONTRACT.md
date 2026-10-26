# Calendario — contrato v1 (2026-10-25)

Vista transversal de recursos propios de Cognova, no calendario personal.
No eventos libres, calendar_events, persistencia duplicada, migraciones ni grants nuevos.
Primera fuente: Actividades existentes sobre 0005_activities; pin Database conservado
604e296e2670d154ba7e18d7afa3f010e66dd42d. No implementa Sesiones, Planes ni Retos.

## Endpoint y filtros

GET /api/v1/calendar, Bearer y onboarding completo obligatorios; no-store.
Query extra=forbid:

- deadline_from y deadline_to obligatorios: ISO 8601 con zona, no fecha sola ni epoch.
- Rango semiabierto [from,to), from < to, máximo 366 días de tiempo transcurrido.
  Filtra el deadline vigente, no el original. Frontend calcula los límites de su zona
  y los envía con offset; no se infiere zona de servidor ni se agrupan días aquí.
- subject_id entero positivo int32 opcional, status y priority de ACTIVITIES_CONTRACT.
  Filtros por AND; todos los estados y materias archivadas incluidos por defecto.
  Materia ajena/inexistente: lista vacía indistinguible, sin consultar su existencia.
- limit=50, entre 1 y 100. Orden deadline ASC, id ASC.
- after_deadline y after_id opcionales pero inseparables: cursor exclusivo por
  (deadline,id), con fecha dentro del rango y ID positivo int32. No exige que el
  recurso del cursor siga existiendo. Conservar rango/filtros al paginar.

200: {items:[CalendarActivityItem],next_cursor:{after_deadline,after_id}|null}.
CalendarActivityItem: id (ID original Activity), type literal "activity", title,
subject_id, deadline, original_deadline, priority, status, estimated_duration.
Sin user_id, notas ni copia del historial. Fechas ISO 8601 con zona. La identidad
pública es (type,id); nunca asumir IDs globales entre futuros tipos.
No se incluye un evento por cambio de fecha: hay un único elemento por actividad.
Lista vacía devuelve items=[] y next_cursor=null. Se leen como máximo limit+1 filas.
Sin snapshot entre páginas: si cambia deadline durante recorrido, refrescar rango;
puede moverse un elemento entre páginas. No prometer vista congelada ni total_count.

## Ejemplo de consulta

GET /api/v1/calendar?deadline_from=2030-01-01T00:00:00Z&deadline_to=2030-02-01T00:00:00Z&limit=50

Conservar estos filtros y añadir los campos devueltos en next_cursor a la siguiente
petición. Codificar el signo + de offsets positivos como %2B al construir la query.
Al recibir next_cursor=null terminó el recorrido. Volver a consultar el rango tras
editar la actividad original; no insertar ni actualizar elementos de calendario.

## Escrituras, seguridad y errores

No POST/PUT/PATCH/DELETE de Calendario: 405. Sin endpoint de detalle duplicado.
Usar /activities/{id}, sus mutaciones y /deadline-history para detalle/edición.
El servicio de Calendario solo ejecuta SELECT con ownership en SQL; no toca historia,
no adquiere locks de escritura, no hace commit ni registra eventos. Auth conserva
su propio comportamiento existente. No recibir user_id del cliente.
401 auth, 403 ONBOARDING_REQUIRED, 422 VALIDATION_ERROR (query inválida),
503 SERVICE_UNAVAILABLE (DB), formato global {error:{code,message}} sin SQL.
Un listado no produce 404 por falta de resultados. CSRF y auth existentes sin cambios.

## Extensión y entrega

DTO de actividad separado, discriminado por type dentro del contenedor de calendario;
servicio de consulta separado de mutaciones. Al incorporar fuentes futuras, ampliar
mediante contrato explícito la unión de DTOs y la paginación/orden total entre tipos.
No reservar endpoints, enums ni tablas ficticias para Sesiones/Planes/Retos ahora.
Contrato/código validados con suite local y CI; desplegados el 2026-10-26 en 61a2f98.
Smoke público y autenticado aprobados; Backend Calendario cerrado el 2026-10-26.
Frontend puede empezar la integración contra el servicio productivo.
Ver PROJECT_STATE e INTEGRATION_VALIDATION.
