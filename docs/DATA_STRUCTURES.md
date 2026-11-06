# Cognova — Estructuras de Datos

## Segundo bloque — IA académica (rama `feat/gemini-behavior`)

Las cinco estructuras nuevas viven en `app/academic_intelligence`, se construyen
por solicitud con una muestra limitada del usuario autenticado y nunca persisten
inferencias. `AcademicContext` las consume al preparar datos para Gemini; el árbol
de viabilidad se consume en `validate_proposal` antes de insertar un Plan.

| Nombre de dominio | Implementación propia | Uso y coste principal |
| --- | --- | --- |
| `PendingAnalysisFlow` | enlaces FIFO entre `PendingAnalysis` | candidatos académicos en orden de llegada; agregar/tomar O(1) |
| `AcademicJourney` | lista simplemente enlazada de `AcademicEvent` | cronología de sesiones y deadlines; anexar O(1), recorrer O(n) |
| `DecisionTrail` | enlaces dobles de `DecisionPassage` | decisiones del usuario en ambos sentidos; anexar O(1), recorrer O(n) |
| `ScheduleIndex` | árbol AVL de `ScheduleEntry` | agenda por instante y recurso; insertar O(log n), consultar rango O(log n + k) |
| `DecisionRoute` | árbol binario de `DecisionBranch` | descartar propuestas sin recursos, fechas o contexto; O(altura) |

PostgreSQL sigue siendo la única fuente de verdad. Los nombres técnicos listados
abajo describen ideas históricas, no clases de este bloque.

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

