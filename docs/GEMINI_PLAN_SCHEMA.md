# Esquema de generación y contrato interno

## Problema y alcance

Google rechazó el esquema completo de `PlanProposal` con HTTP 400:
`The specified schema produces a constraint that has too many states for serving.`

La causa confirmada es la complejidad agregada del decodificador restringido,
no una palabra clave inválida aislada. El esquema original combina listas de
100/200/200 IDs, hasta 30 retos con listas internas de hasta 5 evidencias,
formatos `date-time`, uniones anulables y una definición referenciada.
Las enumeraciones también forman alternativas del decodificador, pero se
conservan. No se ha aislado la contribución individual de cada componente;
`$ref` y `anyOf` no se consideran por sí mismos incompatibles.

## Dos límites de confianza distintos

`gemini_plan_codec.plan_generation_schema()` proyecta el esquema interno a
indicaciones estructurales de generación:

- Conserva **todos** los campos, obligatorios, tipos, enumeraciones, objetos
  cerrados y el objeto abierto `target_value`.
- Expande la definición local de los retos, sin referencias externas.
- Representa las uniones escalares anulables mediante listas de tipos.
- Omite límites de arrays, formatos de fecha y metadatos/restricciones de
  cadenas **solo en el esquema enviado**.
- No recorta arrays, elimina propiedades de una respuesta, inventa valores ni
  repara JSON. Una evolución a uniones más complejas falla explícitamente.

El esquema pasó de 2893 a 1530 caracteres con `json.dumps` en la comprobación
local; el tamaño es una métrica orientativa, no un límite oficial de Google.

`PlanProposal` permanece intacto. `decode_plan_proposal()` valida la respuesta
JSON directamente con ese modelo y `strict=True`: los IDs como cadenas,
booleanos o números flotantes no se convierten a enteros. Fechas y límites
siguen comprobándose localmente. Los valores opcionales conservan únicamente
los defaults definidos en el contrato original.

El proveedor rechaza estados distintos de `completed` antes de aceptar texto;
envía `store=False` y desactiva la continuación automática. La salida de
observaciones mantiene su esquema anterior. No se añade fallback ni se cambia
el modelo principal.

Después de Pydantic, `validate_proposal()` y los validadores de recursos,
relaciones, calendario, evidencia y tamaño siguen decidiendo la aceptación.
`StudyPlanService` conserva generación/validación antes de `_write`; los
recursos se vuelven a validar dentro de la transacción. No se modifica la
persistencia, prioridades, decisiones ni contratos del Frontend.

## Comprobación local y prueba real

- Suite local sin PostgreSQL: **385 passed, 1 skipped**.
- Suite de inteligencia académica con PostgreSQL **desechable y aislado**:
  **13 passed**, incluidos cinco casos nuevos que prueban tanto generación
  como regeneración inválidas. Se mantienen sin cambios los conteos de Planes,
  Retos y Decisiones y el snapshot de la propuesta válida anterior.
- Lint y comprobación de tipos de los módulos modificados.
- No se usan datos existentes para estas pruebas.

Tras las comprobaciones locales se ejecutó **una sola** generación real con
`gemini-3.5-flash-lite`, el esquema simplificado y el proveedor de Cognova,
con contexto ficticio y un reto de finalización de actividad:

- **HTTP 200**, **1,971 s**.
- **Pydantic válido**.
- **Validación de negocio rechazada** (`DomainError`).
- No se conservó la respuesta ni el motivo interno concreto del rechazo;
  no se atribuye a una regla específica sin evidencia.
- `store=False`, sin reintentos ni continuación automática, sin conexión a
  PostgreSQL ni persistencia. La llamada usó un contenedor temporal de solo
  lectura; no alteró el Backend en ejecución.

Esto demuestra que el esquema simplificado fue aceptado por Gemini en esa
prueba, **no** que el modelo haya producido una propuesta íntegramente válida
para Cognova. No habilitar fallback hasta lograr también la validación de
negocio en una prueba autorizada. No se repitió la generación.

Referencias oficiales:

- https://ai.google.dev/gemini-api/docs/structured-output
- https://ai.google.dev/gemini-api/docs/interactions
