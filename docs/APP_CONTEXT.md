# Cognova — Contexto Funcional y Conceptual de la Aplicación

## 1. Qué es Cognova

**Cognova** es una aplicación web de acompañamiento académico con inteligencia artificial.

Su propósito no es únicamente ayudar a organizar tareas o mostrar un calendario. Su valor principal está en **comparar lo que el usuario cree sobre su forma de estudiar con lo que realmente registra haciendo**, para ayudarlo a reflexionar y tomar decisiones más conscientes sobre su vida académica.

Cognova parte de una idea simple:

> Muchas veces una persona cree que sabe qué le funciona para estudiar, pero sus registros pueden mostrar otra cosa.

La aplicación conserva evidencia sobre:

- objetivos;
- materias;
- actividades;
- horarios;
- sesiones de estudio;
- duración;
- resultados;
- aplazamientos;
- cancelaciones;
- motivos;
- retos;
- reflexiones;
- evolución a lo largo del tiempo.

La inteligencia artificial utiliza esa evidencia para detectar diferencias, repeticiones y tendencias.

---

# 2. Qué problema resuelve

Las aplicaciones académicas tradicionales suelen centrarse en:

- listas de tareas;
- calendarios;
- recordatorios;
- fechas límite;
- temporizadores.

Cognova incluye esas herramientas, pero su propósito va más allá.

Busca responder preguntas como:

- ¿Realmente estudio mejor en el horario que creo?
- ¿Las sesiones largas me funcionan mejor que las cortas?
- ¿Qué tipo de actividades aplazo más?
- ¿Cumplo mejor cuando estudio cierta materia a determinada hora?
- ¿Estoy planificando más de lo que realmente puedo cumplir?
- ¿Las estrategias que estoy probando están funcionando?
- ¿Mi percepción inicial coincide con mi comportamiento actual?

La aplicación no responde estas preguntas mediante suposiciones.

Las responde utilizando información registrada por el propio usuario.

---

# 3. Qué NO es Cognova

Es importante que todos los agentes mantengan estos límites.

Cognova **no es**:

- una simple agenda;
- una lista de tareas con un chatbot añadido;
- un chatbot académico genérico;
- una aplicación terapéutica;
- una herramienta para diagnosticar problemas psicológicos;
- un sistema que juzga al estudiante;
- una aplicación basada en frases motivacionales;
- un sistema que pretende descubrir la personalidad del usuario;
- una IA que inventa razones para explicar el comportamiento.

Si una implementación empieza a parecer cualquiera de estas cosas, se está alejando del propósito del producto.

---

# 4. Principio central

La filosofía principal de Cognova es:

> **La IA observa, compara y pregunta. El usuario interpreta y decide.**

La inteligencia artificial no debe decirle al usuario quién es.

Debe ayudarlo a mirar evidencia sobre lo que está haciendo.

---

# 5. Usuario objetivo

Cognova está dirigida principalmente a estudiantes que:

- manejan varias materias;
- planifican actividades;
- quieren mejorar su constancia;
- desean comprender mejor sus hábitos académicos;
- tienden a aplazar ciertas actividades;
- sienten que su planificación no siempre coincide con lo que realmente hacen;
- quieren experimentar con nuevas estrategias de estudio;
- desean tener evidencia sobre qué métodos les funcionan.

No se asume ninguna condición psicológica o médica del usuario.

---

# 6. Flujo conceptual principal

El flujo de Cognova debe conservar esta lógica:

```text
Conocer al usuario
        ↓
Registrar su percepción inicial
        ↓
Definir objetivos y materias
        ↓
Planificar actividades y sesiones
        ↓
Registrar comportamiento real
        ↓
Conservar historial
        ↓
Analizar datos observables
        ↓
Detectar tendencias o contradicciones
        ↓
IA genera observación
        ↓
IA formula pregunta
        ↓
Usuario reflexiona
        ↓
IA puede proponer reto
        ↓
Usuario acepta o rechaza
        ↓
Se registra el resultado
        ↓
El sistema vuelve a analizar
```

Este ciclo es más importante que cualquier pantalla individual.

---

# 7. El cuestionario inicial

El cuestionario representa la **percepción inicial del usuario**.

No debe tratarse como una verdad.

Por ejemplo:

```text
Usuario responde:
"Creo que estudio mejor de noche."
```

Eso no significa que Cognova deba asumir permanentemente que la noche es su mejor horario.

Posteriormente puede comparar esa percepción con los registros.

Ejemplo:

```text
Percepción inicial:
Prefiere estudiar de noche.

Datos después de 3 semanas:
Tarde: 8 sesiones, 6 completadas.
Noche: 7 sesiones, 2 completadas.
```

La IA puede señalar esa diferencia.

No puede afirmar automáticamente una causa.

---

# 8. Cuestionario aprobado

El cuestionario tiene 10 preguntas obligatorias:

1. Objetivo académico principal.
2. Frecuencia de estudio fuera de clases.
3. Momento del día en el que cree que estudia mejor.
4. Duración habitual de las sesiones.
5. Frecuencia con la que cumple lo planificado.
6. Dificultades percibidas para iniciar o terminar.
7. Método actual de organización.
8. Criterio utilizado para priorizar actividades.
9. Reacción habitual cuando una sesión no sale como esperaba.
10. Qué espera comprender o mejorar usando Cognova.

Las preguntas completas y sus opciones viven en `QUESTIONNAIRE.md`.

---

# 9. Planificación académica

El usuario podrá crear:

- materias;
- objetivos;
- actividades;
- fechas límite;
- prioridades;
- sesiones de estudio.

Las actividades serán genéricas y tendrán un tipo.

Tipos sugeridos:

```text
task
exam
project
reading
practice
other
```

Esto evita crear una clase diferente para cada tipo de actividad.

---

# 10. Prioridades

El usuario podrá definir prioridades manuales.

Ejemplos:

```text
low
medium
high
urgent
```

La aplicación también puede usar fecha límite y prioridad para ordenar actividades mediante una estructura de prioridad.

El sistema no debe cambiar automáticamente una prioridad declarada por el usuario sin mostrarlo.

---

# 11. Calendario

El calendario es una parte importante de la experiencia.

Debe permitir visualizar:

- sesiones programadas;
- materia;
- actividad asociada;
- duración;
- fecha;
- hora;
- estado.

El calendario debe sentirse como una herramienta práctica, no como una pantalla decorativa.

---

# 12. Sesiones de estudio

Las sesiones se realizan mediante temporizador.

Flujo esperado:

```text
Sesión programada
        ↓
Usuario inicia temporizador
        ↓
Puede pausar
        ↓
Puede continuar
        ↓
Finaliza
        ↓
Cognova calcula tiempo real
        ↓
Usuario selecciona resultado
```

Resultados posibles:

```text
completed
partial
postponed
cancelled
```

Cuando la sesión no se completa, el usuario puede indicar un motivo.

---

# 13. Motivos

Cognova debe ofrecer motivos frecuentes, pero también permitir uno personalizado.

Ejemplos:

- falta de tiempo;
- interrupción;
- cansancio;
- cambio de prioridad;
- dificultad de la actividad;
- imprevisto;
- otro.

El usuario puede agregar contexto adicional.

Ese contexto es importante porque una semana atípica no debe interpretarse igual que un comportamiento repetido.

---

# 14. Regla: primero se cuestiona el plan

Cuando una sesión falla, Cognova no debe saltar inmediatamente a cuestionar al usuario.

Debe considerar primero si la planificación era realista.

Ejemplos:

- sesión demasiado larga;
- horario difícil;
- varias actividades el mismo día;
- fecha poco realista;
- semana con exámenes;
- imprevisto registrado.

Solo después puede abrir una reflexión sobre la conducta.

---

# 15. Historial

El historial es una pieza central.

Debe conservar:

- sesiones;
- resultados;
- motivos;
- objetivos;
- actividades;
- retos;
- observaciones;
- reflexiones;
- cambios importantes;
- evolución temporal.

El historial permite que Cognova tenga continuidad.

Sin historial, la IA sería solamente un chatbot que responde a lo último que ocurrió.

---

# 16. Umbral mínimo de análisis

Cognova no debe presentar un patrón como significativo con muy pocos datos.

Regla aprobada:

> **Mínimo 5 sesiones registradas antes de hablar de patrones.**

Con menos de 5 sesiones puede mostrar datos descriptivos, pero debe indicar que todavía no hay suficiente evidencia para hablar de una tendencia.

---

# 17. IA como acompañante académico

La IA es una parte central del producto.

No es un extra.

El acompañante debe poder:

- analizar datos del usuario;
- comparar periodos;
- comparar percepción inicial con comportamiento;
- señalar tendencias;
- señalar contradicciones;
- reconocer mejoras;
- formular preguntas;
- conversar sobre esos datos;
- proponer pequeños retos;
- revisar posteriormente si el reto produjo cambios.

---

# 18. Conversación con la IA

La IA será conversacional, pero limitada al ámbito académico.

Ejemplo correcto:

```text
Usuario:
¿Por qué me cuesta tanto completar las sesiones de Estructuras?

IA:
En tus últimos 6 registros de Estructuras completaste 2 sesiones,
mientras que en otras materias completaste 7 de 9.

También veo que 4 de esas 6 sesiones estaban programadas después de las 8 p. m.

Todavía no podemos afirmar que el horario sea la causa,
pero sí parece una diferencia que vale la pena observar.

¿Crees que esas sesiones estaban siendo planificadas en un momento realista para ti?
```

Ejemplo incorrecto:

```text
IA:
Te cuesta Estructuras porque tienes miedo a fracasar.
```

---

# 19. Evidencia antes que opinión

Cada observación debe basarse en datos reales.

Siempre que sea posible debe incluir:

- periodo;
- cantidad de registros;
- proporciones;
- comparación.

Ejemplo:

```text
"En tus últimos 10 registros completaste 4 de 5 sesiones
de menos de 45 minutos y 1 de 5 sesiones de más de 60 minutos."
```

Es mejor que:

```text
"Te funcionan mejor las sesiones cortas."
```

porque la primera conserva evidencia y contexto.

---

# 20. Lenguaje de la IA

La IA debe ser:

- directa;
- reflexiva;
- respetuosa;
- neutral;
- curiosa;
- no complaciente;
- no acusatoria.

Debe evitar:

- regaños;
- sarcasmo hacia el usuario;
- culpa;
- diagnósticos;
- afirmaciones absolutas.

Ejemplos válidos:

```text
"Has aplazado esta actividad cuatro veces."
```

```text
"En estos registros has completado una mayor proporción de sesiones por la tarde."
```

```text
"¿Crees que el horario que estás escogiendo sigue siendo realista?"
```

Ejemplos inválidos:

```text
"Eres procrastinador."
```

```text
"No tienes disciplina."
```

```text
"Saboteas tus propios objetivos."
```

---

# 21. La IA también debe reconocer lo que funciona

Cognova no debe convertirse en una máquina de señalar errores.

También debe mostrar evidencia positiva.

Ejemplo:

```text
"Esta semana completaste las 4 sesiones de 25 minutos que programaste."
```

Esto no es motivación vacía.

Es evidencia sobre una estrategia que aparentemente está funcionando.

---

# 22. Retos

Los retos son experimentos.

No tratamientos.

Ejemplo:

```text
"Durante esta semana prueba tres sesiones de 25 minutos
antes de las 6 p. m. y compara el resultado."
```

La IA propone.

El usuario decide:

```text
Aceptar
Rechazar
```

Una vez aceptado, el reto no se modifica.

Posteriormente Cognova analiza su resultado.

---

# 23. Qué no debe hacer un reto

Incorrecto:

```text
"Como tienes ansiedad con las tareas largas,
debes estudiar en bloques de 25 minutos."
```

Correcto:

```text
"En tus últimos registros las sesiones más cortas tuvieron
mayor cumplimiento. Podemos probar tres sesiones de 25 minutos
esta semana y observar si se mantiene esa diferencia."
```

---

# 24. Racha

La única mecánica de gamificación aprobada es la racha.

Debe ser sencilla.

Mostrar:

- racha actual;
- mejor racha.

No se utilizarán:

- niveles;
- XP;
- monedas;
- recompensas;
- rankings.

Cognova no debe sentirse como un videojuego.

---

# 25. Dependencias académicas

El grafo representa dependencias entre actividades o contenidos.

Ejemplo:

```text
Listas simples
      ↓
Listas dobles
      ↓
Árboles
      ↓
Grafos
```

O:

```text
Actividad A
    ↓
Actividad B
    ↓
Proyecto final
```

Su función debe tener sentido real dentro de la planificación.

---

# 26. Estética

La interfaz debe combinar:

- limpieza estilo Notion;
- colores pastel suaves;
- pequeños elementos cósmicos;
- sensación moderna;
- buen espacio visual;
- navegación sencilla.

Los elementos cósmicos deben ser discretos.

No se busca una interfaz infantil ni saturada de estrellas.

---

# 27. Tema

Debe existir:

- modo claro;
- modo oscuro.

Ambos deben conservar la misma identidad visual.

---

# 28. Personalidad visual de Cognova

Conceptos visuales asociados:

- cognición;
- claridad;
- observación;
- constelaciones;
- conexiones;
- patrones;
- evolución;
- aprendizaje.

La metáfora cósmica puede utilizarse como lenguaje visual:

```text
datos aislados → puntos
relaciones → conexiones
patrones → constelaciones
```

Sin convertirlo en una interfaz temática excesiva.

---

# 29. Experiencia deseada del usuario

El usuario debería sentir que Cognova:

- recuerda su recorrido;
- presta atención a lo que registra;
- no lo juzga;
- no acepta automáticamente todas sus explicaciones;
- le muestra evidencia;
- le permite corregir contexto;
- evoluciona con sus datos;
- hace preguntas útiles.

No debería sentir que:

- está llenando formularios por llenar;
- está hablando con una IA genérica;
- el sistema lo está evaluando moralmente;
- las observaciones son aleatorias.

---

# 30. Registro de bajo esfuerzo

Registrar una sesión debe requerir pocos pasos.

Si el registro es tedioso, los datos perderán calidad.

La UX debe priorizar:

- pocos clics;
- opciones claras;
- valores predefinidos cuando sea posible;
- campos libres solo cuando realmente aporten contexto.

---

# 31. Datos demo

El sistema tendrá seed data.

El objetivo es permitir:

- probar funcionalidades;
- demostrar tendencias;
- probar IA;
- sustentar el proyecto sin esperar semanas de uso real.

Los datos demo deben parecer plausibles y coherentes.

No deben producir patrones absurdos o demasiado perfectos.

---

# 32. Despliegue

Cognova debe quedar desplegada y funcional.

La IA debe funcionar realmente en producción.

No se considera suficiente:

- mock;
- respuesta simulada;
- texto quemado;
- placeholder.

---

# 33. Qué debe priorizarse durante el desarrollo

Orden de prioridad:

```text
1. Correctitud, integridad de datos y seguridad.
2. Mantener coherencia con el propósito de Cognova.
3. Funcionar de forma robusta en escenarios reales.
4. Cumplir todos los requisitos funcionales y de estructuras de datos.
5. Mantener código limpio, modular y POO.
6. Tener buena experiencia visual y accesible.
7. Ser desplegable, observable y recuperable.
8. Funciones adicionales.
```

No usar la naturaleza académica del proyecto como justificación para seguridad débil, mocks permanentes o funcionalidad incompleta.

No agregar funciones extras si comprometen el flujo principal, la seguridad o la estabilidad.

---

# 34. Pregunta de control para agentes

Antes de implementar una funcionalidad, el agente debe poder responder:

> **¿Esta funcionalidad ayuda a registrar, organizar, analizar o reflexionar sobre el comportamiento académico del usuario?**

Si la respuesta es no, probablemente está fuera de alcance.

---

# 35. Resumen corto

Cognova es una aplicación académica que combina:

```text
planificación
+
registro real
+
estructuras de datos
+
análisis
+
IA conversacional
```

para ayudar al usuario a comprender mejor cómo estudia.

No pretende definir al usuario.

Pretende mostrarle evidencia sobre lo que hace.
