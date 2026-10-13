# Onboarding y percepción inicial — contrato 2026-10-12

Base /api/v1; Bearer obligatorio; Cache-Control: no-store; ownership siempre
derivado de sub/sid. Requests extra=forbid; nunca IDs de propietario del cliente.
Errores conservan {error:{code,message}}. 401/422/503 usan el formato global.

## Registro y usuario

POST /auth/register: solo {name,email,password}; name trim 1..30, email válido
normalizado a minúsculas <=50, password 8..12 sin trim. 201 AuthResponse existente
{user,access_token,token_type:"bearer"}, cookies/CSRF/sesión sin cambios.
Los tres campos académicos antiguos se rechazan (422). Duplicado email: 409.
Login conserva emails/passwords antiguos sin aplicar máximos nuevos: no bloquear
cuentas migradas por límites de creación. Error: "Correo o contraseña incorrectos."

UserResponse para registro/login/me y PUT académico:
{id,name,email,degree_program:string|null,semester:integer|null,
onboarding:{status:"incomplete"|"complete",academic_profile_complete:boolean,
questionnaire_complete:boolean,next_step:"academic_profile"|"questionnaire"|"complete"},
legacy_academic_goal:{value:string|null,captured_at:datetime}|null}.
No academic_goal público vigente en User. El valor histórico se lee del archivo
inmutable 0003, preservando incluso espacios/vacíos; no cuenta como cuestionario.
No limitar tamaños de respuestas históricas ni truncar los datos migrados.

Estado calculado en un único servicio, no columna ni string vacío como indicador:
datos académicos = degree_program no vacío tras trim y semester entero >0;
cuestionario = existe revisión inicial completa validada del catálogo admitido.
Ambos = complete. next_step prioriza academic_profile, luego questionnaire.
El usuario puede llenar el cuestionario antes del perfil, seguir autenticado,
restaurar/renovar, listar/revocar sesiones o hacer logout estando incomplete.
Refresh mantiene su respuesta de tokens: frontend consulta /auth/me tras restaurar.

## Datos académicos

PUT /onboarding/academic-profile: {degree_program:string,semester:integer}.
Reemplazo completo e idempotente; trim/no vacío y entero estricto 1..2147483647.
No permite null ni borrar el perfil; no modifica name/email/academic_goal.
200 UserResponse; inválido/extra=422; no autenticado=401.
409 LEGACY_PROFILE_REMEDIATION_REQUIRED si identidad histórica no cumple checks
físicos de name/email de 0003 y actualizarla violaría esos checks. No truncar ni
inventar identidad. Auth/lecturas siguen disponibles; operación debe remediar esos
casos preservando la evidencia, fuera del flujo académico. Rehash se difiere en
esos casos hasta remediación para no romper login por un UPDATE incompatible.

Los futuros subjects/goals/activities/dependencies/study sessions/timer/history/
analytics/streak/AI/challenges requieren complete (403 ONBOARDING_REQUIRED).
Usarán la dependencia get_onboarded_user; no existen endpoints de esos módulos
en esta fase. Auth, catálogo, cuestionario y perfil académico nunca exigen complete.

## Catálogo y respuestas

GET /questionnaire/catalog: 200 {questionnaire_version:1,questions:[
{id,text,selection:"single"|"multi",min_choices:1,max_choices,options:[{id,label}]}]}.
Exactamente q1..q10 y las etiquetas aprobadas en QUESTIONNAIRE.md.

QuestionnaireRequest: {questionnaire_version:1,answers:{q1:Answer,...,q10:Answer}}.
Answer: {choices:[option_id,...],other_text:string|null}; todas las claves q son
obligatorias; single usa lista de longitud 1; multi no vacía y límites 3/2/3 para
q6/q7/q10. IDs exactos, sin duplicados; no se recortan/normalizan IDs desconocidos.
other solo en q1/q6/q7, exige trim 1..50; sin other, rechazar cualquier texto no
nulo (incluso vacío) para evitar ambigüedad. Versión distinta de 1 da 422.

QuestionnaireResponse: {revision:integer,questionnaire_version:1,
answers:{q1:Answer,...,q10:Answer},recorded_at:datetime}.
No user_id ni datos de otros usuarios en responses.

POST /questionnaire: request completo, crea revisión 1; 201 QuestionnaireResponse.
Si ya existe: 409 QUESTIONNAIRE_ALREADY_EXISTS. No reemplaza el baseline.
GET /questionnaire: 200 respuesta de mayor revisión; sin inicial=404 QUESTIONNAIRE_NOT_FOUND.
PUT /questionnaire: request completo más expected_revision:integer estricto >0;
agrega revisión anterior+1 y responde 200. Sin inicial=404; revisión desactualizada
=409 QUESTIONNAIRE_VERSION_CONFLICT. Incluso respuestas idénticas crean revisión:
PUT expresa una nueva declaración; al reintentar con expected_revision vieja da409.
Bloqueo de fila User serializa creación/actualización antes de consultar max revision;
el trigger DB refuerza continuidad. Una transacción, sin UPDATE/DELETE histórico.

GET /questionnaire/history?before_revision=<int>&limit=20: 200
{items:[QuestionnaireResponse,...],next_before_revision:integer|null}.
Orden revision DESC; limit 1..100, before_revision >0 estricto como query entero.
Cursor exclusivo: página siguiente usa la menor revisión devuelta; final=null.
Sin respuestas: items=[]; recorrer páginas permite recuperar revisión1 intacta.

## Persistencia compatible con 0003

DTOs controlados se traducen a JSONB con exactamente q1..q10. Single se persiste
como string ID; multi como lista de IDs. Para Otro se codifica `other:<texto>`
(prefijo reservado, solo opciones other), conservando separadamente en DTO choices
=[...,"other"] y other_text. Los IDs canónicos no contienen ':'; texto libre sí
puede contenerlo y se decodifica quitando solo el primer prefijo. Nunca guardar
objetos anidados o claves extra que el check DB no permite. Catalog version=1
congela esta codificación. Lecturas validan el snapshot antes de devolver DTO.

DB fija: 232c43130c0fb3eddd32e1dd3707368ba0d87d4c, head
0003_onboarding_questionnaire. Backend no ejecuta DDL. Rama no se mergea/deploya
automáticamente: database/operación deben coordinar aplicación de 0003 y permisos
antes del release que exige ese head. Ninguna acción de producción en esta fase.
