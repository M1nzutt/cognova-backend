# Entorno Docker integrado local

## Estado y alcance

Esta guía integra Frontend, Backend y Database localmente. No despliega ni llama a
Render/Netlify y no define servidor, dominio, IP o reverse proxy. La validación se
completó en Docker Desktop / Compose V2 el 2026-11-12. `docker compose config --quiet`
y `docker compose build` pasaron; PostgreSQL 18.6, Backend y Frontend Nginx quedaron
healthy, y migración/grants finalizaron con código 0 en
`0008_ai_plan_proposal_snapshot`. Smoke API/browser, persistencia y backup/restore
local se documentan abajo. Esta configuración no es un perfil de producción para
Internet.

Requiere Docker Engine y Docker Compose V2 2.20+. Las carpetas deben estar juntas:

~~~text
cognova/
  cognova-backend/
  cognova-frontend/
  cognova-database/
~~~

Ejecuta comandos desde cognova-backend. Compose usa una red bridge privada, publica
Frontend solo en 127.0.0.1:8080 y PostgreSQL solo en 127.0.0.1:55432. Backend no
publica puerto de host. PostgreSQL conserva el volumen cognova_pgdata en
/var/lib/postgresql y usa UTF-8/UTC. La salida de red se mantiene disponible para
Gemini. Referencias oficiales: [PostgreSQL](https://hub.docker.com/_/postgres),
[Python](https://hub.docker.com/_/python), [Node](https://hub.docker.com/_/node) y
[Nginx](https://hub.docker.com/_/nginx). La imagen PostgreSQL 18 usa
/var/lib/postgresql como mount del volumen.

## Orden de arranque

- postgres: PostgreSQL 18.6, healthcheck pg_isready y scripts de inicialización local.
- database-migrate: imagen de cognova-database, Alembic ejecuta upgrade head hasta
  0008_ai_plan_proposal_snapshot.
- database-runtime-grants: aplica ACL runtime mínimos después de la migración y
  rechaza hosts, roles o entornos distintos al Compose local.
- backend: Python 3.14.10, no root, dependencias del requirements.lock, launcher
  scripts/start.py; exige Database 0008 antes de escuchar.
- frontend: Node 24.22.3 compila React/TypeScript; Nginx 1.30.6 sirve assets, fallback
  de React Router y proxy same-origin /api hacia backend:8000.

Frontend espera a Backend healthy; Backend espera las migraciones y los grants.
Healthchecks cubren PostgreSQL, Backend /api/v1/health, readiness /api/v1/ready y
Frontend /healthz. Versiones fijadas en los Dockerfiles/Compose.

## Configuración y comandos

Copia solo si no existe un archivo privado y edita sus valores. Si ya hay un .env,
no lo sobrescribas; conserva sus valores privados y añade las variables que falten.
No se debe commitear el archivo privado:

~~~powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -c "import secrets; print(secrets.token_hex(32))"
~~~

Usa valores aleatorios hexadecimales para passwords y al menos 32 bytes para
JWT_SECRET. GEMINI_API_KEY es opcional y solo llega al contenedor Backend; si falta,
Gemini devuelve su respuesta segura de indisponibilidad. No compartas el resultado
de docker compose config porque incluye valores interpolados del .env.

~~~powershell
docker compose config --quiet
docker compose config --services
docker compose build
docker compose up -d
docker compose ps
Invoke-RestMethod http://localhost:8080/api/v1/health
Invoke-RestMethod http://localhost:8080/api/v1/ready
Invoke-WebRequest http://localhost:8080/openapi.json
docker compose exec -T postgres psql -U cognova_admin -d cognova -Atc "SELECT version_num FROM public.alembic_version"
docker compose logs --tail=100 postgres database-migrate database-runtime-grants backend frontend
docker compose down
~~~

La revisión debe ser exactamente 0008_ai_plan_proposal_snapshot. Espera a que
postgres/backend/frontend estén healthy y los dos trabajos de una sola ejecución
terminen con código 0. docker compose down preserva cognova_pgdata; no ejecutes
down -v con información que deba preservarse.

## Smoke funcional integrado

Desde http://localhost:8080 y por los endpoints same-origin /api/*, usando cuentas
sintéticas nuevas:

1. Auth: registro, login, ruta protegida directa, refresh con CSRF, rotación de cookie,
   logout y 401 posterior. Verifica no-store y cookies host-only/SameSite=Lax.
2. Completa onboarding; crea/lista/edita Materia y Actividad; valida filtros e historial.
3. Planifica Sesión con Materia/Actividad, start, pause, resume y finish; comprueba
   intervalos y duración.
4. Comprueba Calendario mensual/semanal con Actividad por deadline y Sesión por
   planned_start_at, filtros, orden simultáneo, detalle y refresh.
5. Comprueba Plan y relaciones, decisiones, Retos y sus transiciones permitidas;
   verifica ownership con una segunda cuenta sintética.
6. Revisa Analytics overview, study-time, timeline y búsqueda.
7. Recorre landing, login/registro, dashboard y rutas de Materias, Actividades,
   Calendario, Planes, Retos, IA y Analytics; prueba refresh, teclado y desktop/móvil.
8. Sin Gemini key, verifica solo la indisponibilidad segura y no declares generación
   real. Con key protegida en Backend, verifica propuesta/snapshot tras refresh,
   decisiones y regenerate; no guardar prompts ni chain-of-thought.

Resultado 2026-11-12: el smoke API se ejecutó con usuarios sintéticos e incluyó Auth,
onboarding, Materias, Actividades, Sesiones/timer, Calendario mixto, Planes, Retos,
ownership y Analytics por el proxy Nginx same-origin. Health/readiness fueron 200 con
`no-store`; las sesiones sintéticas quedaron revocadas. En browser se validaron 11
rutas directas/refresco en desktop y móvil, foco de teclado, sin overflow horizontal
ni errores JS no controlados. Las rutas protegidas redirigieron a login; no se ingresó
auth desde la UI. `GEMINI_API_KEY` no está configurada, así que no se afirma un smoke
Gemini real.

## Backup, restore y persistencia

Se verificó localmente un dump PostgreSQL 18.6 custom con `pg_restore --list` y restore
aislado. Restauró `0008_ai_plan_proposal_snapshot` y coincidieron los counts
sanitizados de las tablas 0001–0007. Dump local:
`%USERPROFILE%\cognova-backups\cognova-local-20261112-204131.dump`; SHA-256
`11820C0ECC41102E706B6312B69666B7ABC121C44B829FE86EB520BEF46EABAD`. Un primer
restore sin usuario explícito intentó usar el rol `root` y falló; la repetición con
`--username=cognova_admin` pasó. También se comprobó persistencia tras `restart` y
`down`/`up`; `cognova_pgdata` sigue presente y no se ejecutó `down -v`.

Para repetir la copia, guárdala fuera de Git y trátala como información académica
sensible. En Windows PowerShell 5, cmd preserva la salida binaria de pg_dump:

~~~powershell
$backupDirectory = Join-Path $env:USERPROFILE 'cognova-backups'
New-Item -ItemType Directory -Force -Path $backupDirectory | Out-Null
$backupFile = Join-Path $backupDirectory 'cognova-local.dump'
cmd /c ('docker compose exec -T postgres pg_dump -U cognova_admin -d cognova --format=custom > "' + $backupFile + '"')
cmd /c ('docker compose exec -T postgres pg_restore --list < "' + $backupFile + '"')
docker compose exec -T postgres createdb -U cognova_admin cognova_restore
cmd /c ('docker compose exec -T postgres pg_restore --username=cognova_admin --exit-on-error --single-transaction --dbname=cognova_restore < "' + $backupFile + '"')
docker compose exec -T postgres psql -U cognova_admin -d cognova_restore -Atc "SELECT version_num FROM public.alembic_version"
~~~

Compara revisión y conteos de origen/restauración. Solo después de verificar, elimina
la base descartable con dropdb. Nunca restaures encima de cognova, automatices
downgrade ni uses down -v fuera de un entorno desechable explícito. Antes de un reset,
haz y comprueba un backup independiente.

## Actualizar, problemas y servidor final

Para actualizar código, checkout de la revisión deseada y repite docker compose build
y up -d. Alembic es la única autoridad del schema. No edites tablas a mano. Los scripts
de /docker-entrypoint-initdb.d solo se ejecutan al crear el volumen inicial; cambiar
.env no rota contraseñas ya creadas.

Si falla migración, grants o Backend, mira logs sanitizados y comprueba revisión 0008,
roles y health/readiness. Si /api falla, confirma backend:8000 dentro de la red. Para
cookies usa exactamente http://localhost:8080; la IP no está permitida por el origin
local. La clave Gemini faltante no impide iniciar el stack.

Esta configuración es HTTP local, no es producción lista para Internet. Aún faltan
SO, dominio, IP, reverse proxy y certificados del servidor. Antes del despliegue se
definirán HTTPS, Secure cookies, origins, TLS de PostgreSQL, secretos, firewall,
puertos publicados y backups. No publiques 8080 directo ni reutilices passwords o
JWT_SECRET de ejemplo.
