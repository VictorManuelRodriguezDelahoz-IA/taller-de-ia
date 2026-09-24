# %% [markdown]
# # Laboratorio: IA en el día a día de DevOps
#
# Taller AI DevOps, ClickIT.
#
# Ustedes ya saben operar pipelines, Terraform y Kubernetes. La pregunta de hoy es otra: ¿en qué partes de
# ese trabajo ayuda de verdad un modelo de lenguaje, y cómo se usa sin que rompa nada?
#
# Vamos a trabajar tres situaciones que todos hemos vivido, y en cada una vamos a ver qué producto de la
# industria ya hace eso:
#
# | Situación | Qué hace la IA | Quién lo hace hoy |
# |---|---|---|
# | Se rompe el pipeline | Lee el log y dice por qué falló y cómo arreglarlo | GitLab Duo (Root Cause Analysis), GitHub Copilot ("Explain error") |
# | Llega un PR de Terraform | Resume el plan y avisa de lo peligroso | Overmind, Spacelift (Saturnhead AI), comentarios de Atlantis |
# | Suena la alerta de guardia | Investiga el clúster con comandos de solo lectura y propone el arreglo | k8sgpt, AWS DevOps Agent, Azure SRE Agent, Datadog Bits AI SRE |
#
# En los tres casos se repite lo mismo, y es lo que queremos que se lleven:
#
# 1. **El contexto lo arma el código.** El modelo solo sabe lo que le pasamos: el log recortado, el diff, el plan.
# 2. **La respuesta sale en un formato que el código pueda revisar**, casi siempre JSON.
# 3. **Las decisiones peligrosas no las toma el modelo.** Bloquear un merge o ejecutar un comando lo decide
#    una regla o una persona.
#
# Un dato para tener en mente: según el reporte DORA 2025, el 90% de los equipos ya usa IA, y la conclusión
# principal es que la IA amplifica lo que ya existe. Con buenas prácticas se va más rápido; sin ellas, se
# rompe más rápido.
#
# Los datos (logs, plan, clúster) son simulados pero están copiados de casos reales. El modelo es real: lo
# llamamos por OpenRouter. Para usarlo, creen el archivo `laboratorios/.env` con la línea
# `OPENROUTER_API_KEY=...`. Sin clave, el notebook usa respuestas guardadas de una ejecución real.

# %%
import sys, os, json, time, re
import urllib.request, urllib.error
from pathlib import Path

RAIZ = Path.cwd() if (Path.cwd() / "devops_ia.py").exists() else Path.cwd().parent
sys.path.insert(0, str(RAIZ))

import devops_ia as D
from aiops import mostrar, mostrar_markdown, mostrar_codigo, tarjeta, tabla, mensaje_chat, texto_html

MODELO = "anthropic/claude-haiku-4.5"

# %% [markdown]
# ## Conectarnos al modelo
#
# Llamar a un LLM es hacer un POST con la clave en una cabecera y la conversación en el cuerpo. OpenRouter
# usa el mismo formato que OpenAI, así que este código sirve casi igual para OpenAI, Azure OpenAI, vLLM u
# Ollama. Lo escribimos sin librerías para que se vea todo.
#
# Todas las llamadas pasan por `llamar()`. Es nuestro gateway: ahí anotamos tokens, tiempo y costo, y ahí
# se agregarían los reintentos, el caché o el cambio de proveedor.

# %%
def leer_clave():
    clave = os.environ.get("OPENROUTER_API_KEY", "")
    env = RAIZ / ".env"
    if not clave and env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if linea.startswith("OPENROUTER_API_KEY="):
                clave = linea.split("=", 1)[1].strip()
    return clave

def cargar_precios():
    # precio por token de cada modelo, del catálogo público de OpenRouter
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"User-Agent": "taller"})
        catalogo = json.loads(urllib.request.urlopen(req, timeout=20).read())["data"]
        return {m["id"]: (float(m["pricing"]["prompt"]), float(m["pricing"]["completion"])) for m in catalogo}
    except Exception:
        return {}

API_KEY = leer_clave()
PRECIOS = cargar_precios()
print("Modelo:", MODELO if API_KEY else "respuestas guardadas (no encontré la clave)")

# %%
URL = "https://openrouter.ai/api/v1/chat/completions"
LLAMADAS = []

def llamar(mensajes, paso, herramientas=None, modelo=None):
    modelo = modelo or MODELO
    inicio = time.time()
    if not API_KEY:
        mensaje, (tokens_in, tokens_out) = D.respuesta_guardada(paso)
    else:
        cuerpo = {"model": modelo, "messages": mensajes, "temperature": 0.2, "max_tokens": 1500}
        if herramientas:
            cuerpo["tools"] = herramientas
        req = urllib.request.Request(URL, data=json.dumps(cuerpo).encode("utf-8"),
                                     headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"})
        for intento in range(3):
            try:
                respuesta = json.loads(urllib.request.urlopen(req, timeout=120).read())
                break
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503) or intento == 2:
                    raise RuntimeError("OpenRouter devolvió %d: %s" % (e.code, e.read().decode()[:200]))
                time.sleep(2 ** intento)     # límite de uso o error del proveedor: esperamos y reintentamos
        mensaje = respuesta["choices"][0]["message"]
        tokens_in, tokens_out = respuesta["usage"]["prompt_tokens"], respuesta["usage"]["completion_tokens"]
    precio_in, precio_out = PRECIOS.get(modelo, (0, 0))
    LLAMADAS.append({"paso": paso, "modelo": modelo, "tokens entrada": tokens_in, "tokens salida": tokens_out,
                     "segundos": round(time.time() - inicio, 1),
                     "costo USD": round(tokens_in * precio_in + tokens_out * precio_out, 5), "mensaje": mensaje})
    return mensaje

def preguntar(prompt, paso, modelo=None):
    return llamar([{"role": "user", "content": prompt}], paso, modelo=modelo)["content"]

def leer_json(texto):
    # los modelos a veces envuelven el JSON en ```json ... ```; nos quedamos con lo que está entre llaves
    try:
        return json.loads(texto[texto.index("{"): texto.rindex("}") + 1])
    except ValueError:
        return {}

print(preguntar("En una frase: ¿qué es un error budget?", paso="prueba"))

# %% [markdown]
# ## Caso 1: se rompió el pipeline
#
# Laura subió un cambio para que la imagen de Docker pese menos y el pipeline de GitHub Actions falló. Este
# es el log, tal cual:

# %%
mostrar_codigo(D.LOG_CI, titulo="build.yml, job build (falló)")
print(len(D.LOG_CI.splitlines()), "líneas,", len(D.LOG_CI), "caracteres")

# %% [markdown]
# Este log es corto. En la vida real un job de CI escupe miles de líneas, y mandarlas todas cuesta dinero,
# tarda más y además confunde al modelo. GitLab Duo, por ejemplo, manda solo el final del log (los últimos
# 100.000 caracteres).
#
# Nosotros hacemos algo parecido: nos quedamos con las líneas de error y unas pocas alrededor, y con el
# final del log. Fíjense que el aviso de Node.js 16 también entra: es ruido, pero no queremos esconderle
# nada al modelo que pueda importar.

# %%
def recortar_log(log, alrededor=3, final=8):
    lineas = log.splitlines()
    conservar = set(range(len(lineas) - final, len(lineas)))
    for i, linea in enumerate(lineas):
        if re.search(r"error|warning|failed|exception", linea, re.IGNORECASE):
            conservar.update(range(i - alrededor, i + alrededor + 1))
    # quitamos la marca de tiempo de GitHub, que no aporta nada y gasta tokens
    return "\n".join(re.sub(r"^\S+Z ", "", lineas[i]) for i in sorted(conservar) if 0 <= i < len(lineas))

LOG_RECORTADO = recortar_log(D.LOG_CI)
print("De %d a %d caracteres." % (len(D.LOG_CI), len(LOG_RECORTADO)))

# %% [markdown]
# Ahora le pedimos el diagnóstico. Lo vamos a hacer dos veces: primero solo con el log, y después con el log
# y el diff del commit. Así se ve cuánto cambia la respuesta según el contexto que le damos.

# %%
PROMPT_CI = """Eres un ingeniero DevOps revisando un job de CI que falló.

Responde solo con un JSON con estas claves:
- "causa": qué falló, en una frase
- "por_que_ahora": por qué empezó a fallar justo en este commit, o "no se puede saber" si no hay datos
- "arreglo": el cambio concreto a hacer, en una o dos frases (qué archivo y qué cambiar)
- "es_flaky": true si parece un fallo intermitente que se arregla reintentando

{contexto}"""

contextos = {
    "solo el log": "Log del job:\n" + LOG_RECORTADO,
    "log + diff del commit": "Log del job:\n" + LOG_RECORTADO + "\n\nÚltimo commit:\n" + D.DIFF_CI,
}

filas = []
for nombre, contexto in contextos.items():
    diagnostico = leer_json(preguntar(PROMPT_CI.format(contexto=contexto), paso="CI: " + nombre))
    filas.append({"contexto": nombre, "causa": diagnostico.get("causa"), "¿por qué ahora?": diagnostico.get("por_que_ahora"),
                  "arreglo": diagnostico.get("arreglo"), "¿flaky?": diagnostico.get("es_flaky")})

mostrar(tabla(filas, ["contexto", "causa", "¿por qué ahora?", "arreglo", "¿flaky?"], titulo="Diagnóstico del pipeline"))

# %% [markdown]
# Comparen las dos filas. Con solo el log, el modelo encuentra el error (falta `pg_config`), pero el "por qué
# ahora" lo tiene que adivinar. Con el diff lo confirma: la imagen `slim` no trae las librerías de PostgreSQL
# que sí traía la imagen completa. Con eso Laura puede decidir con criterio entre cambiar a `psycopg2-binary`
# o instalar `libpq-dev` en el Dockerfile.
#
# Por eso las herramientas serias no solo mandan el log: GitLab Duo también manda la configuración del
# pipeline y los cambios recientes. El modelo es el mismo; lo que cambia es el contexto.
#
# El campo `es_flaky` es un ejemplo de algo útil para automatizar: si el modelo dice que es intermitente, el
# pipeline podría reintentar solo, y si no, avisar al autor del commit con el diagnóstico.

# %% [markdown]
# ## Caso 2: revisar un PR de Terraform
#
# Diego abrió el PR #318: "Cifrar la base de pedidos y abrir SSH para el bastión". El pipeline corrió
# `terraform plan` y guardó el resultado con `terraform show -json plan.out`. Así se ve resumido:

# %%
ACCION = {("create",): "crear", ("update",): "modificar", ("delete",): "borrar",
          ("delete", "create"): "REEMPLAZAR (borra y crea)", ("create", "delete"): "reemplazar (crea y borra)"}

cambios = D.PLAN_TF["resource_changes"]
mostrar(tabla([{"recurso": c["address"], "acción": ACCION[tuple(c["change"]["actions"])]} for c in cambios],
              ["recurso", "acción"], titulo="PR #318: %s" % D.PR_TF["titulo"]))

# %% [markdown]
# Cinco cambios. Un revisor apurado ve "cifrar la base" y aprueba. Pero ese `REEMPLAZAR` quiere decir que
# Terraform va a borrar la base de producción y crear una nueva vacía, porque `storage_encrypted` no se puede
# cambiar en una instancia que ya existe.
#
# Para esto ya existen reglas: OPA, Sentinel o checkov revisan el plan con condiciones fijas. Escribimos
# tres de ese estilo. Son código, así que siempre dan el mismo resultado, y eso es lo que queremos para
# bloquear un merge.

# %%
CON_DATOS = ("aws_db_instance", "aws_rds_cluster", "aws_s3_bucket", "aws_dynamodb_table", "aws_efs_file_system")

def revisar_con_reglas(cambios):
    hallazgos = []
    for c in cambios:
        acciones, despues = c["change"]["actions"], c["change"]["after"] or {}
        if "delete" in acciones and c["type"] in CON_DATOS:
            hallazgos.append({"recurso": c["address"], "regla": "Borra un recurso con datos", "severidad": "alta"})
        if c["type"] == "aws_security_group_rule" and "0.0.0.0/0" in despues.get("cidr_blocks", []) \
                and despues.get("from_port") not in (80, 443):
            hallazgos.append({"recurso": c["address"], "regla": "Puerto %s abierto a internet" % despues["from_port"],
                              "severidad": "alta"})
        if c["type"].startswith("aws_iam") and re.search(r'"[a-z0-9]+:\*"|"\*"', despues.get("policy", "")):
            hallazgos.append({"recurso": c["address"], "regla": "Permisos IAM con comodín", "severidad": "media"})
    return hallazgos

HALLAZGOS = revisar_con_reglas(cambios)
mostrar(tabla(HALLAZGOS, ["recurso", "regla", "severidad"], titulo="Lo que encuentran las reglas"))

# %% [markdown]
# Las reglas son buenas para decir *qué* está mal, pero no explican nada, y solo ven lo que alguien pensó
# de antemano. Ahí entra la IA, que es lo que hacen Overmind o Spacelift: leer el plan completo, explicarlo en
# lenguaje de persona y buscar riesgos que no están en ninguna regla.

# %%
PROMPT_TF = """Eres un ingeniero de plataforma revisando un PR de Terraform que va a producción.
Abajo está el plan en JSON y lo que ya encontraron las reglas automáticas.

Responde solo con un JSON con estas claves:
- "resumen": qué hace este PR en 2 frases, para el revisor
- "riesgos_adicionales": lista de {{"recurso", "riesgo", "severidad"}} (alta, media o baja) solo con
  los riesgos que las reglas NO detectaron. No repitas los hallazgos de las reglas.
- "preguntas": 2 o 3 preguntas concretas que el revisor debería hacerle al autor

PR: {pr}

Hallazgos de las reglas:
{hallazgos}

Plan:
{plan}"""

revision = leer_json(preguntar(PROMPT_TF.format(pr=json.dumps(D.PR_TF, ensure_ascii=False),
                                                hallazgos=json.dumps(HALLAZGOS, ensure_ascii=False),
                                                plan=json.dumps(cambios)), paso="revisar plan"))

adicionales = revision.get("riesgos_adicionales") or []

mostrar(tarjeta("Resumen del PR", [("resumen", revision.get("resumen", "-"))], color="#7c3aed"))
mostrar(tabla(adicionales, ["recurso", "riesgo", "severidad"], titulo="Lo que encontró la IA y no las reglas"))

# %% [markdown]
# En este plan hay al menos dos cosas que ninguna de nuestras reglas mira: la base también baja de
# `db.r6g.large` a `db.t3.medium`, y tiene `skip_final_snapshot = true`, así que al borrarla no queda ni un
# snapshot. Vean si la IA las encontró. Una regla solo las detecta si alguien la escribió antes.
#
# Con todo esto armamos el comentario que el bot deja en el PR. La decisión de bloquear el merge la toman
# **solo las reglas**: la IA puede dar resultados distintos en cada ejecución, y un gate tiene que ser
# reproducible. Lo que aporta la IA va como información para el revisor.

# %%
bloquear = any(h["severidad"] == "alta" for h in HALLAZGOS)

comentario = "**Revisión automática del plan**\n\n" + revision.get("resumen", "") + "\n\n"
comentario += "Encontrado por las reglas:\n"
comentario += "\n".join("- **%s** (%s): %s" % (h["recurso"], h["severidad"], h["regla"]) for h in HALLAZGOS)
comentario += "\n\nSugerido por la IA:\n"
comentario += "\n".join("- **%s** (%s): %s" % (r.get("recurso"), r.get("severidad"), r.get("riesgo")) for r in adicionales)
comentario += "\n\n**Preguntas para @%s:**\n" % D.PR_TF["autor"]
comentario += "\n".join("- " + p for p in revision.get("preguntas") or [])
comentario += "\n\n" + ("⛔ Merge bloqueado por las reglas: hace falta la aprobación de un owner de plataforma."
                        if bloquear else "✅ Las reglas no encontraron nada bloqueante.")
mostrar_markdown(comentario)

# %% [markdown]
# ## Caso 3: suena la alerta y un agente investiga
#
# 3:20 de la mañana. Alerta: *"deployment/checkout en tienda: el rollout no progresa"*.
#
# Esto es lo que hacen los "AI SRE": AWS DevOps Agent, Azure SRE Agent, Datadog Bits AI SRE o, en open
# source, k8sgpt. Cuando llega la alerta, un agente investiga solo con comandos, arma una hipótesis y la deja
# lista para quien está de guardia.
#
# La diferencia con los casos anteriores es que aquí el modelo no recibe todo el contexto de entrada. Recibe
# **herramientas**: funciones que puede pedir que ejecutemos, y él decide cuáles usar y en qué orden. Le
# damos solo herramientas de lectura. Es lo que recomiendan hoy todos: empezar en modo lectura (Azure lo llama
# *Reader mode*) y pasar a actuar solo con aprobación.
#
# Las herramientas se describen con un nombre, una descripción y sus parámetros. Esa descripción es lo único
# que el modelo sabe de cada una, así que hay que escribirla bien.

# %%
def herramienta(nombre, descripcion, parametros):
    return {"type": "function", "function": {
        "name": nombre, "description": descripcion,
        "parameters": {"type": "object", "properties": {p: {"type": t} for p, t in parametros.items()},
                       "required": list(parametros)}}}

HERRAMIENTAS = [
    herramienta("get_pods", "kubectl get pods -n <namespace>", {"namespace": "string"}),
    herramienta("describe_pod", "kubectl describe pod <nombre> -n tienda. Necesita el nombre completo del pod, "
                              "como sale en get_pods", {"nombre": "string"}),
    herramienta("logs", "kubectl logs <pod> -n tienda. previous=true trae los logs del contenedor anterior "
                        "(útil si está en CrashLoopBackOff)", {"pod": "string", "previous": "boolean"}),
    herramienta("get_events", "kubectl get events -n <namespace> ordenados por tiempo", {"namespace": "string"}),
    herramienta("rollout_history", "kubectl rollout history deployment/<deployment> -n tienda", {"deployment": "string"}),
    herramienta("get_configmap", "kubectl describe configmap <nombre> -n tienda. El nombre exacto aparece en "
                               "describe_pod, en 'Environment Variables from'", {"nombre": "string"}),
]

# lo que ejecutamos de verdad cuando el modelo pide una herramienta
FUNCIONES = {"get_pods": D.get_pods, "describe_pod": D.describe_pod, "logs": D.logs,
             "get_events": D.get_events, "rollout_history": D.rollout_history, "get_configmap": D.get_configmap}

# %% [markdown]
# Y este es el agente. Es un bucle, igual al de la sesión 1: el modelo pide una herramienta, la ejecutamos,
# le devolvemos el resultado y vuelve a pensar. Termina cuando responde sin pedir herramientas, o cuando se
# acaban los pasos: un agente sin tope de pasos puede quedarse dando vueltas y gastando.
#
# Fíjense en una línea: si el modelo pide algo que no está en `FUNCIONES`, no se ejecuta. En producción esa
# protección no depende del prompt, sino de los permisos: la service account del agente tiene RBAC de solo
# lectura, y aunque el modelo quisiera borrar un pod, Kubernetes no lo dejaría.

# %%
PROMPT_AGENTE = """Eres el ingeniero de guardia (SRE) de la tienda. Llegó esta alerta:
"deployment/checkout en el namespace tienda: el rollout no progresa".

Investiga con las herramientas que tienes (todas son de solo lectura). Busca la causa raíz, no el síntoma.
Si un comando devuelve NotFound, revisa el nombre exacto antes de sacar conclusiones.
Cuando la tengas, responde solo con un JSON:
{"causa": "...", "evidencia": ["lo que viste y en qué comando"],
 "comando_sugerido": "UN solo comando kubectl, el más seguro para recuperar el servicio ahora",
 "alternativa": "el arreglo definitivo, para hacer con calma", "reversible": true/false}"""

mensajes = [{"role": "user", "content": PROMPT_AGENTE}]
MAXIMO_PASOS = 8

for paso in range(1, MAXIMO_PASOS + 1):
    respuesta = llamar(mensajes, paso="agente", herramientas=HERRAMIENTAS)
    mensajes.append(respuesta)
    if not respuesta.get("tool_calls"):
        break
    for llamada in respuesta["tool_calls"]:
        nombre = llamada["function"]["name"]
        argumentos = json.loads(llamada["function"]["arguments"] or "{}")
        if nombre in FUNCIONES:
            resultado = FUNCIONES[nombre](**argumentos)
        else:
            resultado = "Herramienta no permitida: " + nombre
        print("paso %d  $ %s %s" % (paso, nombre, " ".join("%s=%s" % a for a in argumentos.items())))
        mensajes.append({"role": "tool", "tool_call_id": llamada["id"], "content": resultado})
else:
    print("Se acabaron los pasos sin conclusión: se pasa el caso a una persona.")

DIAGNOSTICO = leer_json(respuesta.get("content") or "")

# %%
mostrar(tarjeta("Diagnóstico del agente", [
    ("causa", DIAGNOSTICO.get("causa", "-")),
    ("evidencia", " | ".join(DIAGNOSTICO.get("evidencia") or [])),
    ("comando sugerido", DIAGNOSTICO.get("comando_sugerido", "-")),
    ("alternativa", DIAGNOSTICO.get("alternativa", "-")),
    ("¿reversible?", "sí" if DIAGNOSTICO.get("reversible") else "no"),
], color="#16a34a"))

# %% [markdown]
# Vale la pena ver el camino que siguió: normalmente mira los pods, ve el `CrashLoopBackOff`, lee los logs
# del contenedor anterior (`KeyError: 'DATABASE_URL'`), revisa el ConfigMap (que tiene `DB_URL`) y el
# historial del rollout, donde la versión 2.14.0 dice justamente "renombra DB_URL a DATABASE_URL". Es lo mismo
# que haría una persona, pero en segundos y a las 3 de la mañana.
#
# Igual, revisen la evidencia que cita. Un agente puede pedir un nombre equivocado, recibir un `NotFound` y
# concluir algo falso con total seguridad. Por eso la evidencia va en el mensaje y el comando lo aprueba una
# persona. Y por eso las descripciones de las herramientas dicen de dónde sacar cada nombre.
#
# Ahora, el agente **no ejecuta** el arreglo. Lo que hacen estos productos es mandar la propuesta al canal
# del incidente y esperar a que alguien la apruebe (Azure lo llama *Review mode*). Hagamos eso: el modelo
# redacta el mensaje y el código decide si se ejecuta.

# %%
mensaje = preguntar("Escribe el mensaje que el agente de guardia publica en el canal #incidentes de Slack. "
                    "Texto plano, máximo 6 líneas, para ingenieros. Di qué pasa, la causa con su evidencia y "
                    "el comando propuesto, y termina pidiendo que respondan APROBAR o RECHAZAR.\n\n"
                    + json.dumps(DIAGNOSTICO, ensure_ascii=False), paso="mensaje slack")
mostrar(mensaje_chat("#incidentes", mensaje))

# %%
APROBADO = False     # esto lo cambia una persona desde Slack, no el modelo

comando = DIAGNOSTICO.get("comando_sugerido", "")
if not comando.startswith("kubectl"):
    print("El comando no es de kubectl: no se ejecuta nada.")
elif APROBADO:
    print("Aprobado. Se ejecutaría:", comando)
else:
    print("Esperando aprobación. No se ejecuta nada.")

# %% [markdown]
# ## ¿Cuánto costó todo esto?
#
# Como todo pasó por `llamar()`, tenemos el detalle de cada llamada.

# %%
mostrar(tabla(LLAMADAS, ["paso", "modelo", "tokens entrada", "tokens salida", "segundos", "costo USD"],
              titulo="Llamadas al modelo"))
print("Total: %d llamadas y %.4f USD." % (len(LLAMADAS), sum(f["costo USD"] for f in LLAMADAS)))

# %% [markdown]
# Fíjense en qué paso gasta más: el agente. Cada vuelta del bucle le reenvía toda la conversación al modelo,
# así que los tokens de entrada crecen en cada paso. Por eso los agentes necesitan tope de pasos y conviene
# que las herramientas devuelvan salidas cortas.
#
# ## Ejercicios
#
# **1. Su propio pipeline.** Copien el log de un job que les haya fallado de verdad (GitHub Actions, GitLab,
# Jenkins, lo que usen), péguenlo en `MI_LOG` y ejecuten. Antes de pegarlo, quiten secretos y datos internos:
# lo que mandan al modelo sale de su red.

# %%
MI_LOG = """
"""     # TODO: peguen aquí su log

if MI_LOG.strip():
    diagnostico = leer_json(preguntar(PROMPT_CI.format(contexto="Log del job:\n" + recortar_log(MI_LOG)), paso="mi log"))
    mostrar(tarjeta("Diagnóstico de mi pipeline", [(k, str(v)) for k, v in diagnostico.items()], color="#7c3aed"))
else:
    print("Peguen un log en MI_LOG para probar.")

# %% [markdown]
# **2. ¿Qué modelo usar?** Mismo prompt del caso 1, cuatro modelos. Comparen si encuentran la causa, cuánto
# tardan y cuánto cuestan. Para diagnosticar un pipeline, ¿vale la pena el modelo caro?

# %%
MODELOS = ["anthropic/claude-haiku-4.5", "anthropic/claude-sonnet-5", "openai/gpt-4o-mini", "google/gemini-2.5-flash"]

filas = []
for modelo in MODELOS:
    try:
        d = leer_json(preguntar(PROMPT_CI.format(contexto=contextos["log + diff del commit"]),
                                paso="comparar: " + modelo, modelo=modelo))
    except RuntimeError as error:
        filas.append({"modelo": modelo, "causa": str(error)[:100]})
        continue
    filas.append({"modelo": modelo, "causa": d.get("causa"), "¿por qué ahora?": d.get("por_que_ahora"),
                  "segundos": LLAMADAS[-1]["segundos"], "costo USD": LLAMADAS[-1]["costo USD"]})

mostrar(tabla(filas, ["modelo", "causa", "¿por qué ahora?", "segundos", "costo USD"], titulo="Mismo log, cuatro modelos"))

# %% [markdown]
# **3. Para pensar en equipo.** Si mañana dejaran que el agente del caso 3 ejecute solo el
# `kubectl rollout undo`, ¿qué condiciones le pondrían? Piensen en: si la acción se puede deshacer, a qué
# servicios aplica, en qué horario y qué pasa si el rollback no arregla nada.
#
# ## Para llevarse
#
# Si el lunes quieren empezar a usar esto en su equipo, este es un orden razonable:
#
# 1. **Empezar por leer y explicar**: diagnosticar pipelines rotos, resumir planes de Terraform, resumir
#    alertas. Si el modelo se equivoca, no rompe nada.
# 2. **Cuidar el contexto**: recortar logs, agregar el diff, mandar solo lo que sirve. Mejora la respuesta
#    y baja el costo.
# 3. **Pedir JSON y revisarlo con código** antes de usar la respuesta para algo.
# 4. **Dejar los gates en reglas deterministas.** La IA informa al revisor; no decide el merge.
# 5. **Agentes con permisos de solo lectura** (RBAC, IAM), tope de pasos y una persona que aprueba cualquier
#    cambio.
# 6. **Medir** cuánto cuesta y cuánto tarda cada uso, y probarlo con casos reales antes de confiar en él. Eso
#    es lo que vimos en la sesión 2 con el set dorado.
