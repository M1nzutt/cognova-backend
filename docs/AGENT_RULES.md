# Cognova — Reglas para Agentes

## Alcance vigente — 2026-10-25

Materias y Actividades están cerrados en Backend. Schema productivo: `0005_activities`.
Calendario v1 autorizado como vista transversal de solo lectura de Actividades.
Contrato: [CALENDAR_CONTRACT](CALENDAR_CONTRACT.md). Sin eventos libres, schema
nuevo ni implementación de Sesiones/Planes/Retos; futuras fuentes requieren contrato.

Release autorizado y cerrado 2026-10-26: merge --no-ff, deploy Render y smoke.
La autorización posterior permitió cuentas/datos sintéticos mínimos por API,
credenciales aleatorias solo en memoria, limpieza segura y revocación de sesiones.
Sustituye el bloqueo anterior por falta de credenciales; no permite cuentas reales,
cambios en otros repositorios ni migraciones. Evidencia y cierre en PROJECT_STATE.

## Antes de trabajar

1. Leer `APP_CONTEXT.md`.
2. Leer `PROJECT_STATE.md`.
3. Leer todos los documentos maestros.
4. Revisar:
   - `git status`
   - `git diff`
   - `git log --oneline -15`

Nunca asumir que una tarea interrumpida quedó terminada.

## Alcance de repositorio y base de datos

- Actividades autorizadas 2026-10-23: consumir 0005 en
  604e296e2670d154ba7e18d7afa3f010e66dd42d. Leer ACTIVITIES_CONTRACT.
  Sustituye exclusiones históricas de actividades; no autoriza producción ni otros repos.

- Materias (2026-10-18): leer SUBJECTS_CONTRACT.md; consumir 0004_subjects al SHA
  c3394c38c55a8cd466d10f02fe7c80d7c1e1980f. No modificar auth ni implementar
  actividades, frontend o IA. Las referencias 0003 anteriores son históricas.

- Este agente trabaja únicamente en `cognova-backend`.
- La arquitectura vigente tiene tres repositorios: frontend, backend y database.
- Backend conserva modelos ORM SQLAlchemy, queries y conexión PostgreSQL.
- Database es propietario de Alembic, revisiones, schema lifecycle, índices,
  constraints físicos, seeds DB y backup/restauración.
- No modificar otros repositorios; documentar exactamente los cambios que requieren.
- Desde fase 2 no crear ni restaurar historial Alembic o DDL en startup backend.
  CI consume el commit database fijado en `tools/database-ref.json`; actualizarlo
  requiere evidencia PostgreSQL y compatibilidad ORM/auth. Alembic dev no concede
  ownership de migraciones. Ver [DATABASE_HANDOFF.md](DATABASE_HANDOFF.md).
- Prohibido recrear esquema, borrar/squash historial, cambiar revision IDs o usar
  `create_all`/`stamp` como sustituto del traspaso.
- No rehacer auth ni despliegue por un PROJECT_STATE antiguo: contrastar Git/código.

## Fuente de verdad

Los documentos compartidos definen el producto y los contratos.

Orden de prioridad ante conflicto:

1. seguridad y contrato explícito más reciente;
2. `AUTH_CONTRACT.md` para autenticación;
3. `API_CONTRACT.md`;
4. `DECISIONS.md`;
5. `APP_CONTEXT.md`;
6. estado real del código.

Si documentos y código se contradicen:
- no elegir arbitrariamente;
- registrar la contradicción;
- migrar de forma deliberada;
- actualizar documentación.

## Estándar

Cognova se construye como aplicación real de producción.

No usar “es solo un proyecto académico” para justificar:
- seguridad débil;
- mocks permanentes;
- deuda técnica evitable;
- datos inseguros;
- endpoints improvisados;
- código no probado.

## POO

- una clase relevante por archivo;
- responsabilidad única;
- encapsulamiento;
- composición;
- herencia/polimorfismo solo cuando aporten valor;
- no crear clases artificiales solo para aparentar POO.

## Prohibido

- archivos gigantes;
- varias clases importantes por archivo;
- lógica de negocio pesada en routers/controllers;
- acceso DB desde frontend;
- acceso del frontend al proveedor de IA;
- secretos en código;
- endpoints fuera del contrato;
- cambiar stack sin documentarlo;
- reemplazar estructuras manuales por colecciones nativas y presentarlas como implementación;
- un único commit final;
- tokens de autenticación en `localStorage`/`sessionStorage`;
- desactivar controles de seguridad para “hacer que funcione”;
- inventar decisiones faltantes importantes sin documentarlas.

## Contratos antes que implementación

Antes de implementar una funcionalidad cuyo request/response no esté definido:
1. completar el contrato;
2. actualizar el contrato local y documentar sincronización con los repos afectados;
3. luego implementar.

No inferir DTO público directamente desde tablas.

## Seguridad

Leer siempre `SECURITY_BASELINE.md`.

No reducir estándares sin una decisión explícita y documentada.

## Pruebas

Cada fase debe incluir las pruebas correspondientes.

No considerar “funciona en mi máquina” como validación suficiente.

## Git

Objetivo de evolución: superar 500 commits útiles por repositorio. No crear commits
vacíos/falsos ni dividir cambios artificialmente; no hacer squash que destruya
historial útil. Registrar `git rev-list --count HEAD` cuando ayude a la continuidad,
sin priorizar el conteo sobre correctitud o estabilidad. Este agente solo aporta
commits reales en backend; no modifica el historial de los otros repositorios.

Después de un bloque coherente:
1. ejecutar pruebas;
2. ejecutar lint/type/build aplicable;
3. revisar `git diff`;
4. actualizar docs;
5. actualizar `PROJECT_STATE.md`;
6. commit pequeño y coherente.

## Si faltan tokens/contexto

Detener tareas grandes.

Antes de terminar:
- dejar repo estable si es posible;
- documentar archivos tocados;
- documentar pruebas ejecutadas;
- documentar errores conocidos;
- documentar siguiente paso exacto;
- hacer commit solo si el bloque está estable.

## Continuación

Un agente nuevo debe poder reconstruir el estado leyendo `PROJECT_STATE.md`, Git y los documentos sin depender del chat anterior.
