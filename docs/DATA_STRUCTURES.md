# Cognova — Estructuras de Datos

- Stack: historial de acciones reversibles.
- Queue: análisis pendientes.
- SinglyLinkedList: feed cronológico.
- DoublyLinkedList: navegación anterior/siguiente.
- CircularLinkedList: ciclo semanal.
- BinaryTree: árbol de decisión sobre viabilidad del plan.
- BinarySearchTree: índice ordenado por fecha/duración.
- AVLTree: índice balanceado.
- NaryTree: objetivo → materia → actividad → sesión.
- Graph: dependencias académicas, BFS, DFS, path_exists.
- HashTable: acceso rápido por ID.
- MinHeap/PriorityQueue: prioridad + deadline.
- Trie: autocompletado.

Reglas: implementación manual, una clase por archivo, nodos auxiliares separados, pruebas unitarias, uso real.

## Reglas de integración

- PostgreSQL sigue siendo la fuente persistente de datos.
- Las estructuras se implementan manualmente para cumplir su función algorítmica real; no sustituyen la base de datos.
- Cada estructura debe tener pruebas unitarias y al menos un caso de uso integrado cuando corresponda.
- No mantener dos fuentes de verdad inconsistentes entre estructura en memoria y DB.
- Documentar complejidad esperada de operaciones principales.

