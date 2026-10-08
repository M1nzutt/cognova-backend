# Cognova — Reglas para Agentes

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

- Este agente trabaja únicamente en `cognova-backend`.
- La arquitectura vigente tiene tres repositorios: frontend, backend y database.
- Backend conserva modelos ORM SQLAlchemy, queries y conexión PostgreSQL.
- Database es propietario de Alembic, revisiones, schema lifecycle, índices,
  constraints físicos, seeds DB y backup/restauración.
- No modificar otros repositorios; documentar exactamente los cambios que requieren.
- El historial local y la migración en startup son transitorios. No eliminarlos ni
  añadir revisiones nuevas aquí sin resolver antes el corte descrito en
  [DATABASE_HANDOFF.md](DATABASE_HANDOFF.md).
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
