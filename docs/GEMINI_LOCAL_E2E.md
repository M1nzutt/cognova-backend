# Modelo configurable y validación desde la aplicación

## Configuración

`GEMINI_MODEL` es una variable exclusiva del Backend. Se valida como un
identificador Gemini, sin espacios, rutas ni caracteres de control.

```dotenv
GEMINI_MODEL=gemini-3.5-flash-lite
```

Sin variable, se conserva el valor histórico `gemini-3.8-flash`. `.env.example`
incluye el candidato validado y `compose.yaml` transmite la variable al Backend.
No se activa facturación ni se configura otro proveedor. La clave sigue siendo
un secreto de entorno del proceso Backend, nunca una variable `VITE_*`.

Las rutas de Planes y observaciones reciben el modelo desde `Settings`. Cada
instancia de `GeminiProvider` lo utiliza para la solicitud y sus logs seguros.
Los snapshots de generación y regeneración guardan ese mismo modelo. Un cambio
posterior no modifica snapshots históricos; las decisiones conservan el modelo
de su propuesta original.

Se desactivan los reintentos del SDK y la continuación automática: una
operación genera como máximo una solicitud upstream. No se introduce fallback
ni reparación de propuestas. Pydantic, reglas de negocio, ownership,
validaciones de escritura y atomicidad permanecen activas.

## Verificaciones automatizadas

- Backend sin PostgreSQL: **437 aprobadas, 1 omitida**.
- Inteligencia académica con PostgreSQL desechable: **18 aprobadas**.
  Incluye propagación real de Settings -> ruta -> proveedor -> snapshot,
  cambio de modelo al regenerar y preservación de la propuesta anterior en
  decisiones. Las respuestas del SDK son sintéticas en esta suite.
- Ruff y mypy de los cinco módulos Backend modificados aprobados.
- Frontend: `npm run verify` aprobado, **390 pruebas**, lint, tipos y build.
  Se mantienen avisos previos de PostCSS y tamaño del bundle.

## Único flujo con Gemini real

La prueba usó código actual en un Backend local separado
(`cognova-gemini-local`, puerto `18000`) y el Frontend local (`5180`), contra
PostgreSQL local. No se sustituyeron ni reiniciaron los servicios existentes.
Todas las escrituras pertenecen a una cuenta sintética nueva; no se consultaron
cuentas o recursos de estudiantes reales.

Evidencia de la ejecución:

- Cuenta sintética `35`, Plan `22`, reto `20`.
- Modelo persistido: `gemini-3.5-flash-lite`.
- **Una sola llamada real**; no regeneración ni llamada de observaciones.
- Generación desde botón autenticado: **HTTP 201**, **2017 ms** de recorrido;
  log seguro del proveedor: **1847 ms**, `result=ok`.
- Plan `ai/draft` y un reto contextual visibles en la interfaz.
- Refresh conserva la propuesta original y sus recursos.
- Aceptación desde UI: **HTTP 200**, Plan `active`, una decisión `accepted`.
- Otro refresh conserva el estado activo, el snapshot original y la decisión.
- Inicio del reto desde UI: **HTTP 200**, estado `in_progress` persistente tras
  refresh. Ninguna generación adicional.
- Cero errores JavaScript no controlados.
- SELECT limitado a la cuenta/Plan sintéticos confirma modelo, estado, un reto
  y una aceptación. No se guardan prompts, tokens, credenciales ni salida cruda.

Dos intentos previos del harness se detuvieron durante la preparación de
fixtures (longitud de contraseña/nombre de materia), **sin consumir Gemini**.
La cuenta sintética incompleta `34` se conserva; no se borraron registros.

El recorrido real eligió **aceptar**, no rechazar: las dos decisiones son
excluyentes sobre la misma propuesta. El rechazo se cubre por las suites
existentes; no se generó otro Plan para repetirlo.

## Reproducción explícita

El Frontend incluye `scripts/smokeGeminiPlanBrowser.ts`. Solo admite origen
HTTP loopback y exige consentimiento explícito para una generación. Crea su
propia cuenta, no utiliza credenciales de un estudiante y conserva las
propuestas/decisiones sintéticas como evidencia.

```powershell
$env:SMOKE_LOCAL_URL = 'http://127.0.0.1:5180'
$env:SMOKE_ALLOW_GEMINI_GENERATION = '1'
node --experimental-strip-types scripts/smokeGeminiPlanBrowser.ts
```

No ejecutar por rutina: cada ejecución autorizada puede consumir una
generación. El harness bloquea una segunda generación, regeneraciones y
observaciones durante el recorrido. El resumen local
`.local/gemini-plan-e2e.json` contiene únicamente métricas, IDs sintéticos,
comprobaciones y estados HTTP, no la propuesta ni credenciales.

La instancia local de validación utiliza `GEMINI_MODEL=gemini-3.5-flash-lite`
solo en su entorno. No se modifica el `.env` privado ni se realiza despliegue,
push o merge. Los cambios de configuración se aplican al iniciar el Backend
correspondiente, no a procesos ya iniciados.
