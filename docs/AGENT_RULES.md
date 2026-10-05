# Cognova — Reglas para Agentes

## Antes de trabajar
Leer `APP_CONTEXT.md` primero para comprender qué es Cognova y qué no debe convertirse.

Leer todos los documentos maestros, revisar `git status` y últimos commits.

## Si falta contexto
No inventar. Reconstruir estado leyendo docs + código.

## Si hay contradicción
No elegir arbitrariamente. Documentarla y resolverla.

## POO
- una clase relevante por archivo;
- responsabilidad única;
- encapsulamiento y composición;
- herencia/polimorfismo solo si aportan valor.

## Prohibido
- archivos gigantes;
- varias clases importantes por archivo;
- lógica pesada en routers;
- acceso DB desde frontend;
- secretos en código;
- endpoints fuera del contrato;
- cambiar stack sin autorización;
- reemplazar estructuras manuales por colecciones nativas;
- un único commit final.

## Cierre de tarea
1. Ejecutar pruebas.
2. Revisar git diff.
3. Actualizar docs afectadas.
4. Actualizar PROJECT_STATE.md.
5. Hacer commit pequeño y coherente.

## Si faltan tokens/contexto
Detener tareas grandes, guardar estado, documentar siguiente paso y dejar el repo estable.
