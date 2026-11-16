# Diagnóstico seguro de propuestas IA

## Qué se puede concluir

La prueba anterior recibió HTTP 200 y pasó Pydantic, pero descartó la respuesta
y el motivo de negocio. **No se puede reconstruir retrospectivamente la regla
incumplida.** Los casos siguientes reproducen rechazos posibles y demostrables,
no se atribuyen sin evidencia al resultado histórico.

Se comprobaron dos desajustes concretos:

1. El enum interno permite `custom`, pero `validate_proposal()` prohíbe ese
   objetivo para IA (`ai_custom_target_forbidden`). Las instrucciones no lo
   prohibían expresamente ni explicaban las formas exactas de `target_value`.
   Un objetivo de actividad con `{"status":"completada"}` pasa `PlanProposal`
   pero falla `activity_completion_target`; las claves y valores de protocolo
   no se deben traducir.
2. `PlanProposal` permite un datetime de reto sin zona horaria. Su comparación
   con las fechas conscientes del Plan provocaba `TypeError`, fuera de la
   traducción segura a `DomainError`. Ahora se rechaza antes de comparar,
   mediante `challenge_timezone`. No se acepta ni se repara esa fecha.

## Cambios

Las instrucciones especifican los cuatro tipos de objetivos IA válidos, sus
valores exactos, contexto, IDs relacionados, fechas dentro del Plan, evidencia
vinculada, unicidad y límites. El esquema y `PlanProposal` no se modifican.

Cada fallo de `validate_proposal()` produce únicamente:

```text
ai_proposal_rejected rule=<identificador_estatico> code=AI_PROPOSAL_RULE_REJECTED
```

No se registran prompts, texto de propuesta, IDs, catálogo, errores Pydantic
completos, stack traces ni datos del usuario. Los errores de los modelos de
escritura se clasifican por tipos y una lista cerrada de mensajes conocidos;
un error no reconocido recibe un identificador genérico, nunca se imprime.
El error público sigue siendo `STUDY_PLAN_GENERATION_UNAVAILABLE`.

Los controles originales permanecen activos:

| Grupo | Reglas de rechazo |
| --- | --- |
| Plan | Recursos propios y al menos una materia, contexto existente, IDs positivos de 32 bits y únicos, texto válido, fechas con zona y fin posterior al inicio |
| Relaciones del reto | Materia incluida en Plan; actividad/sesión incluida, de la misma materia y coherente entre sí; objetivo relacionado y de tipo correcto |
| Fechas del reto | Zona horaria, intervalo dentro del Plan, deadline no anterior al inicio |
| Evidencia | Evidencia y condición presentes, todas las citas en catálogo, al menos una vinculada al reto, actividad o sesión registrada para esa materia |
| Objetivos | No `custom` para IA; formas exactas para minutos, actividad, sesión y dominio; tamaños JSON permitidos |
| Integridad | Retos no duplicados, recursos presentes en contexto, rechazo seguro de contexto inconsistente |

Los campos opcionales del esquema pueden ser obligatorios condicionalmente:
por ejemplo, todo reto IA necesita `subject_id`, aunque el campo interno
admita `null`. No se debilitan esas condiciones para facilitar la generación.

## Verificaciones

- **430 pruebas locales aprobadas, 1 omitida**. Incluyen 38 casos sintéticos
  estructuralmente válidos que ejercitan rechazos de negocio, una defensa de
  evidencia vacía, cuatro objetivos válidos y comprobaciones de logs seguros.
- **17 pruebas de inteligencia académica aprobadas en PostgreSQL desechable**.
  Nueve variantes inválidas pasan por generación y regeneración; no cambian
  los conteos de Planes/Retos/Decisiones ni el snapshot de la propuesta válida.
  No se usan datos académicos existentes.
- Ruff y mypy de los módulos modificados aprobados.
- La base y la transacción de escritura no cambian. Los controles adicionales
  de ownership/relaciones/calendario se siguen ejecutando en la transacción
  antes de guardar; las decisiones y contratos del Frontend se mantienen.

## Única prueba real posterior

Se ejecutó una sola solicitud con `gemini-3.5-flash-lite`, datos sintéticos,
el proveedor de Cognova y el mismo esquema simplificado. Solo el adaptador de
prueba seleccionó el modelo alternativo; el modelo principal sigue intacto.

- **HTTP 200; 2,267 segundos**.
- **Pydantic: PASS**.
- **`validate_proposal()`: PASS**, con un reto contextual.
- `store=False`, reintentos cero y continuación automática desactivada.
- Sin PostgreSQL en la prueba real, sin persistir ni mostrar la propuesta.
- Contenedor temporal de solo lectura, sin modificar el Backend en ejecución.

Es evidencia de éxito para ese contexto sintético, no una garantía universal
de calidad ni prueba causal del fallo histórico. No se añade fallback, no se
cambia de proveedor y no se hace push, merge ni deploy.
