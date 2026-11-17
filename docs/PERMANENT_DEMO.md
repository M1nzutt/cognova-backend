# Cuenta permanente: Lucia Torres / TurnoClaro

## Estado real de la preparación

**Cuenta académica operativa; componente Gemini pendiente. No presentar esta
preparación como seis semanas de uso real ni como una demo IA terminada.**

- Dirección local: `http://localhost:8080`.
- Identidad ficticia: **Lucia Torres Demo**, `demo.software@example.com`.
- Propietaria local: usuario `36`; nunca se reutilizan cuentas de terceros.
- Carrera: Ingeniería de Software, semestre 5.
- Proyecto transversal ficticio: **TurnoClaro**, software de reservas sin datos
  de pacientes ni personas reales.
- Referencia congelada: **2026-11-16**. En otra instalación se elige al crearla.

El preparador utiliza exclusivamente rutas HTTP oficiales. No contiene SQL,
migraciones, resets, borrados de recursos ni operaciones sobre volúmenes.

## Contenido disponible

| Módulo | Preparación comprobada |
| --- | --- |
| Materias | 5: Requisitos, Arquitectura, Bases de Datos, Calidad y Pruebas, Gestión Ágil |
| Actividades | 30; 10 completadas, 5 en progreso, 15 pendientes; prioridades y fechas diferentes |
| Historial de actividades | 3 revisiones de fechas mediante PATCH oficial |
| Sesiones | 37: 36 previstas inicialmente y un reemplazo de ensayo interrumpido |
| Temporizador | 1 ensayo completado de diez minutos; 4 parciales de un minuto; intervalos reales comprobados |
| Otros resultados | 1 aplazada y 2 canceladas; 29 planificadas, incluida una futura lista para iniciar |
| Planes | `24` Fundamentos, completado; `25` Ruta revisada, activo |
| Decisiones | Edición real del borrador manual antes de activarlo |
| Retos manuales | 6: 2 completados, 1 fallido, 1 en progreso y 2 pendientes |
| Dependencias | Validar prototipo depende de Criterios de aceptación, mediante el campo oficial del reto |
| Calendario | Seis semanas de fechas planificadas y una sesión futura adicional |
| Analytics | Métricas reales, con la advertencia de interrupción descrita abajo |
| IA | 0 propuestas persistidas; 3 intentos registrados y detenidos sin reintento automático |

Cada materia aporta seis hitos semanales relacionados: entrevistas -> historias
-> criterios -> prototipo -> validación -> entrega; contexto -> componentes ->
REST -> servicios -> seguridad -> integración; entidades -> normalización ->
consultas -> índices -> transacciones -> persistencia; y recorridos análogos
de pruebas y gestión. No son registros aleatorios.

La evolución de estados se hizo mediante POST/PUT/PATCH oficiales. Las fechas
de creación y decisiones son las reales del proceso, no fechas inventadas.
Los estados de retos son decisiones manuales válidas, no certificaciones
automáticas de que una actividad o aprendizaje ocurrió en una fecha pasada.

## Limitación temporal y recuperación tras el reinicio

Las API permiten planificar fechas pasadas. No permiten importar `start_at`,
`end_at`, intervalos o fechas históricas de decisiones. El reloj del servidor
determina esos datos. Analytics agrega intervalos, no fechas de planificación.

Por tanto, **las seis semanas representan una trayectoria planificada ficticia**.
El tiempo efectivamente registrado empieza al preparar la cuenta. Para disponer
de seis semanas reales de Analytics hay que continuar utilizándola seis semanas
con el temporizador real; no existe una API legítima de backfill.

El reinicio del entorno interrumpió un ensayo de Bases de Datos (`55`) mientras
el temporizador permanecía abierto. Se cerró mediante `finish/cancelled`, con
`context=other` y explicación técnica. Se conservaron **45662,422572 segundos**
de intervalo; no se recortaron ni eliminaron. Se creó el reemplazo mediante
POST oficial, sin editar el plan activo, operación que sus reglas no permiten.

Los cinco ensayos válidos suman **840,735370 segundos**, unos **14 minutos**.
Analytics excluye las sesiones canceladas del tiempo estudiado y expone su
duración por separado. Para esta cuenta debe mostrar aproximadamente **14 minutos
de estudio** y **761 minutos de temporizador cancelado excluidos**. Todos los
intervalos originales permanecen intactos; no se borraron ni acortaron datos.

La sustentación debe señalar esta diferencia. La sesión cancelada conserva el
motivo en su detalle y el informe privado separa
`valid_rehearsal_seconds` de `recovery_incidents`.

## Gemini: registro y bloqueo actual

Modelo: `gemini-3.5-flash-lite`, sin fallback ni reintentos automáticos.

| Intento | Resultado comprobado |
| --- | --- |
| 1 | API 503; operación fallida, sin propuesta persistida. Causa interna exacta no retenida |
| 2 | Gemini/Pydantic válidos; rechazo de negocio `challenge_target_relation`; ninguna escritura parcial |
| 3 | HTTP 503 del proveedor, confirmado por diagnóstico seguro; ninguna propuesta persistida |

Se hicieron **tres solicitudes reales** para esta cuenta. Se agotó el presupuesto
explícito de esta preparación. El verificador de navegador no consume Gemini.
No se copiaron propuestas de otra cuenta ni se inventaron respuestas, explicaciones
o snapshots.

En la revisión posterior se autorizó condicionalmente un cuarto intento, solo
después de aprobar también PostgreSQL. No se consumió ni se aumentó el presupuesto:
el Docker Engine local no estuvo disponible, por lo que no fue posible ejecutar
esas pruebas. No hacer otra llamada hasta repetir las regresiones PostgreSQL y
obtener autorización vigente.

Se añadieron dos mejoras conservadoras: espera configurable
`GEMINI_TIMEOUT_MS` (15000 por defecto; local 60000, rango 1000–120000) y
diagnósticos de fallo sin prompts/respuestas/credenciales. El identificador
genérico opcional `target_id` se pide como `null`; los objetivos conservan
sus enlaces tipados y todas las comprobaciones de negocio.

**Pendiente:** una propuesta auténtica editada/aceptada y una segunda propuesta
contextual con decisión de rechazo. Requiere disponibilidad del proveedor y
autorización para ampliar el presupuesto. No se vuelve a crear el semestre ni
a ejecutar los ensayos para retomarlo.

## Credenciales y estado privado

Directorio local, fuera de ambos repositorios:

```text
C:\Users\sarav\.local\state\cognova\demo\
```

- `credentials.dpapi`: cifrado DPAPI del usuario Windows actual.
- `progress.json`: propietario, IDs, pasos y presupuesto consumido; sin tokens.
- `report.json`: métricas, límites y estado real; no contiene respuestas Gemini.
- `prepare.lock`: bloqueo transitorio de proceso; no es un registro académico.

`report.json` es una lectura generada por la última fase `verify`; tras cambios
de reglas de Analytics, regenerarlo con las API disponibles antes de usar sus
totales. El reporte anterior puede reflejar la regla histórica que contaba
temporizadores cancelados dentro del estudio.

En Linux se usa `credentials.json` con modo `0600`, dentro de directorio `0700`.
No se almacena una API Key en estas herramientas: Gemini solo la lee el Backend.
La contraseña cumple el contrato de 8–12 caracteres y no está en Git.

Para consultar **localmente** las credenciales como operador:

```powershell
py -3.14 -m scripts.prepare_demo credentials
```

Este comando revela la contraseña deliberadamente en la terminal del operador.
No pegar su salida en chats, capturas, logs, tickets o commits. DPAPI no es
portable a otra máquina/usuario; guardar una copia en un gestor de contraseñas,
no copiar el cifrado a la VPS esperando que se descifre.

## Reproducir en otra instalación / VPS (sin despliegue automático)

Prerrequisitos: Cognova ya está instalado con esquema compatible, HTTPS y
configuración Gemini válida. Las herramientas son Python estándar y se ejecutan
desde el checkout Backend; no instalan dependencias ni modifican el esquema.
Estos comandos son un procedimiento, **no se han ejecutado en la VPS**.

```bash
# Elegir referencia solo al crear esta instalación de la demo.
python3 -m scripts.prepare_demo prepare \
  --base-url https://TU-DOMINIO \
  --state-dir "$HOME/.local/state/cognova/demo" \
  --reference YYYY-MM-DD --apply --allow-ai

# Mantener en primer plano: diez minutos reales + cuatro parciales de un minuto.
python3 -m scripts.prepare_demo timers \
  --base-url https://TU-DOMINIO --apply

# Solo después de aceptar la primera propuesta y tener los cinco ensayos.
python3 -m scripts.prepare_demo context \
  --base-url https://TU-DOMINIO --apply --allow-ai

python3 -m scripts.prepare_demo verify --base-url https://TU-DOMINIO
```

Usar el mismo `--state-dir` en todos los pasos si se cambia el directorio por
defecto. No copiar `progress.json` local a otra instalación: los IDs y el
origen pertenecen a esa base. La identidad ficticia es estable, pero las
credenciales de cada instalación son independientes.

### Idempotencia y errores

- Los IDs y la referencia se congelan en el journal. Repetir `prepare` no
  reinicia estados, no cambia decisiones del usuario y no genera duplicados.
- Las creaciones con respuesta perdida se reconcilian por sus claves. Un
  resultado ambiguo detiene el proceso en lugar de reenviar un POST.
- Cada intento Gemini se descuenta **antes** de enviarse, incluso si falla.
- `--retry-failed-ai` es una acción explícita del operador, nunca una política
  automática. Antes hay que confirmar que no existe una propuesta persistida
  ni una operación en curso.
- `--ai-budget N` autoriza un total acumulado de intentos para ese journal
  (por defecto 2; máximo 10). No reinicia el contador. **No ampliar el presupuesto
  actual de 3 sin una nueva autorización.**
- Si el proceso se interrumpe, revisar el PID de `prepare.lock`. Retirar
  exclusivamente ese bloqueo si el proceso ya no existe; no borrar el journal
  ni las credenciales. Un temporizador abierto se cancela conservando intervalos:
  `recover-timer --apply --subject-key bd`.
- El modo `verify` admite que el estudiante agregue más recursos después. No
  interpreta esa continuidad como permiso para restaurar o borrar sus cambios.

Se comprobó una repetición real: **cero escrituras académicas**, mismas huellas
de recursos y mismo número de intentos Gemini.

Las pruebas locales aprobaron **462 casos Backend (1 omitido)** y **391
Frontend**, además de lint, tipos y build. Las pruebas nuevas cubren los
contratos, fechas relativas, protección de credenciales, paginación, estados
ambiguos, presupuesto, no repetición de temporizadores y recuperación.
No se ejecutaron migraciones ni pruebas que necesiten crear esquemas en esta
preparación. La corrección posterior de Analytics suma regresiones PostgreSQL
que requieren ejecutar un servidor desechable. En la última revisión se
aprobaron 462 pruebas unitarias Backend y 391 Frontend; las pruebas PostgreSQL
no se ejecutaron porque el Docker Engine estaba desconectado. Tampoco se pudo
volver a ejecutar la verificación autenticada del navegador mientras los
servicios locales permanecieron apagados.

## Verificación de navegador

Desde Frontend:

```bash
node --experimental-strip-types scripts/verifyPermanentDemoBrowser.ts
```

Usa exclusivamente las credenciales privadas de esta cuenta. Bloquea escrituras
académicas y llamadas Gemini; permite login/logout/refresh. Comprueba Dashboard,
materias, actividades, sesiones, temporizador futuro, calendario mensual/semanal,
planes, retos, decisiones, Analytics, refresh y logout/login.

Evidencias locales ignoradas por Git:

```text
cognova-frontend/.local/permanent-demo/*.png
cognova-frontend/.local/permanent-demo/browser-report.json
```

La ejecución pasó los módulos disponibles con cero errores de API/JavaScript.
El informe marca `complete=false` y `pending_modules` para los dos planes IA,
sin declarar una verificación que no ocurrió. Código de salida `2` significa
preparación incompleta, no un fallo de login o pérdida de datos.

## Guion breve recomendado (con las limitaciones explícitas)

1. Iniciar sesión en la cuenta ficticia; explicar TurnoClaro y la referencia.
2. Materias -> actividades: seguir una historia de requisitos hasta su entrega;
   mostrar prioridad y una revisión real de fecha límite.
3. Calendario mensual y semanal: distinguir compromiso planificado de ejecución.
4. Sesiones: mostrar intervalos del ensayo completado, un parcial, una sesión
   aplazada y la futura preparada para el temporizador.
5. Plan Fundamentos completado -> Ruta revisada activa; mostrar edición,
   dependencia y retos completados/fallidos/en progreso/pendientes.
6. Analytics: mostrar los cinco ensayos, aclarar que las semanas previas no
   contienen estudio retroactivo y señalar el intervalo técnico cancelado.
7. Cuando Gemini vuelva a funcionar y se autoricen las llamadas pendientes:
   revisar explicación/snapshot, editar y aceptar, luego comparar con una
   nueva propuesta contextual y la decisión de rechazo. **Este paso no está
   disponible todavía y no debe simularse.**
8. Recargar, cerrar sesión y volver a entrar para demostrar persistencia.
