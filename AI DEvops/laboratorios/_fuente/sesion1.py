# %% [markdown]
# # Sesion 1 - Fundamentos y arquitectura
#
# **Taller AI DevOps - ClickIT** | Laboratorio de la sesion 1
#
# En la sesion viste seis ideas. Aqui las vas a **ver pasar**:
#
# | # | Idea de la sesion | Lo que haras aqui |
# |---|---|---|
# | 1 | Predice, no consulta | Provocar una alucinacion y cerrarla |
# | 2 | No es determinista | Medir cuantas respuestas distintas da el mismo prompt |
# | 3 | Formato roto | Contar cuantas salidas rompen tu parser, y arreglarlo |
# | 4 | El contexto es un escritorio | Medir tokens y costo de lo que mandas |
# | 5 | Todo bucle necesita frenos | Construir un bucle con topes y romperlo |
# | 6 | Estado, nodos y aristas | Construir un grafo con ciclo y aprobacion humana |
# | 7 | Todo sale por el gateway | Rutear en cascada y medir el ahorro |
#
# **No necesitas API key.** Los modelos `sim-small` y `sim-large` son un simulador
# local que imita el comportamiento de un LLM real (no determinismo, formato roto,
# alucinacion, costo, latencia y fallos). Si tienes clave, cambia `MODELO` por un
# modelo real y todo sigue funcionando igual.
#
# > Ejecuta las celdas en orden con **Shift + Enter**. Las celdas marcadas
# > **EJERCICIO** tienen un `TODO` para ti.

# %%
# --- Preparacion (ejecuta esta celda primero) ---
import sys, json, statistics, time
from pathlib import Path

RAIZ = Path.cwd()
if not (RAIZ / "lab_utils.py").exists():
    RAIZ = RAIZ.parent
sys.path.insert(0, str(RAIZ))

import lab_utils as L
from lab_utils import chat, contar_tokens, tabla, barra

MODELO = "sim-small"        # cambia a "sim-large" o a un modelo real si tienes clave
print("Listo. Modelos disponibles sin clave:", [m for m in L.PRECIOS if m.startswith("sim")])
print("Casos del set dorado:", len(L.cargar_golden()))

# %% [markdown]
# ---
# ## 1. Predice, no consulta
#
# Un LLM no busca en una base de datos: continua el texto de forma plausible.
# Cuando no tiene el dato, no se calla: **lo inventa con el mismo tono seguro**.
#
# Vamos a preguntarle algo que SI esta en un documento, y algo que NO esta.

# %%
runbook = L.documento("runbook_incidentes.md")

def preguntar(pregunta, contexto, prohibir_inventar=False):
    prompt = "Responde usando solo el contexto.\n"
    if prohibir_inventar:
        prompt += "Si la respuesta no esta en el contexto, responde exactamente NO_SE.\n"
    prompt += "<contexto>\n" + contexto + "\n</contexto>\n\nPregunta: " + pregunta
    return chat(prompt, modelo=MODELO, temperature=0).texto

print("A) Dato que SI esta en el runbook")
print("   ", preguntar("cual es el objetivo de tiempo para completar un rollback", runbook), "\n")

print("B) Dato que NO esta en el runbook (mira el tono de seguridad)")
print("   ", preguntar("cual es el plazo maximo para cerrar un postmortem", runbook), "\n")

print("C) Mismo dato ausente, pero prohibiendo inventar")
print("   ", preguntar("cual es el plazo maximo para cerrar un postmortem", runbook,
                       prohibir_inventar=True))

# %% [markdown]
# **Lo que acabas de ver:** la respuesta B es falsa y suena igual de segura que la A.
# La unica diferencia entre B y C es **una linea de instruccion**. Ese es el control
# mas barato que existe: darle una salida honesta cuando no sabe.

# %% [markdown]
# ---
# ## 2. No es determinista (y la temperatura lo empeora)
#
# Slide: *"si tu sistema depende de que la respuesta sea siempre identica, el problema
# no se arregla con el prompt"*. Vamos a medirlo.

# %%
TICKET = ("Tras el deploy de anoche el pod del servicio de pagos consume el doble de "
          "memoria y devuelve error 500 a muchos usuarios. servicio: pagos-api")

p = L.cargar_prompt("clasificar_incidente.v1.yaml")
prompt = L.render(p["plantilla"], ticket=TICKET)

def variacion(temperatura, n=8):
    salidas = [chat(prompt, modelo=MODELO, temperature=temperatura, formato_json=True).texto
               for _ in range(n)]
    return len(set(salidas)), salidas

for t in (0.0, 0.3, 0.7, 1.0):
    distintas, salidas = variacion(t)
    print("temperature=%.1f -> %d respuestas distintas de 8   %s"
          % (t, distintas, barra(distintas / 8, 16)))

print("\nEjemplo de una salida:", salidas[0][:120])

# %% [markdown]
# ### EJERCICIO 1
#
# 1. Sube `n` a 20 y vuelve a correr. Con `temperature=0`, **cuantas distintas salen?**
#    (Pista: casi nunca es 1. Eso es "casi repetible no es repetible".)
# 2. Rellena el TODO: calcula la **respuesta mayoritaria** de 10 llamadas a
#    `temperature=0.7`. Es el patron *self-consistency*: votar en vez de confiar.

# %%
from collections import Counter

def respuesta_mayoritaria(prompt, n=10, temperatura=0.7):
    # TODO: llama n veces, quedate con el campo "categoria" de cada respuesta
    #       y devuelve (categoria_mas_votada, votos, n)
    votos = Counter()
    for _ in range(n):
        r = chat(prompt, modelo=MODELO, temperature=temperatura, formato_json=True)
        ...   # <-- TODO: extrae r.json()["categoria"] y cuentalo en `votos`
    if not votos:
        return None, 0, n
    cat, v = votos.most_common(1)[0]
    return cat, v, n

print(respuesta_mayoritaria(prompt))
# Esperado cuando lo resuelvas: ('aplicacion', ~7-10, 10)

# %% [markdown]
# ---
# ## 3. Formato roto -> salida estructurada
#
# El fallo mas caro no es que se equivoque: es que rompa tu integracion.
# Tres niveles de control, de peor a mejor.

# %%
prompt_flojo = "Clasifica este ticket y dime la categoria y la severidad.\n\nTicket: " + TICKET
prompt_exigente = prompt          # el v1 ya dice "Responde UNICAMENTE con un JSON"

def tasa_json_valido(pr, n=20, forzar=False):
    ok = 0
    for _ in range(n):
        r = chat(pr, modelo=MODELO, temperature=0.7, formato_json=forzar)
        try:
            r.json(); ok += 1
        except Exception:
            pass
    return ok / n

filas = [
    {"control": "1. pedir sin exigir formato", "json_valido": tasa_json_valido(prompt_flojo)},
    {"control": "2. exigir formato en el prompt", "json_valido": tasa_json_valido(prompt_exigente)},
    {"control": "3. salida estructurada (schema)", "json_valido": tasa_json_valido(prompt_exigente, forzar=True)},
]
tabla(filas)
print("\nAsi se ve una salida del nivel 1:")
print(chat(prompt_flojo, modelo=MODELO, temperature=0.7).texto[:200])

# %% [markdown]
# ### Validacion local + reintento con el error
#
# Aunque el proveedor prometa el esquema, **la validacion es tuya**. Y si falla,
# se reintenta pasandole el error concreto (suele resolverse al primer reintento).

# %%
ESQUEMA = {
    "categoria": {"tipo": str, "valores": L.CATEGORIAS, "obligatorio": True},
    "severidad": {"tipo": str, "valores": L.SEVERIDADES, "obligatorio": True},
    "servicio":  {"tipo": str, "obligatorio": True},
    "requiere_humano": {"tipo": bool, "obligatorio": True},
}

def validar(d, esquema=ESQUEMA):
    """Devuelve lista de errores. Vacia = valido."""
    errores = []
    if not isinstance(d, dict):
        return ["la salida no es un objeto JSON"]
    for campo, regla in esquema.items():
        if campo not in d:
            if regla.get("obligatorio"):
                errores.append("falta el campo obligatorio '%s'" % campo)
            continue
        v = d[campo]
        if not isinstance(v, regla["tipo"]):
            errores.append("'%s' deberia ser %s y es %s" % (campo, regla["tipo"].__name__, type(v).__name__))
        if "valores" in regla and v not in regla["valores"]:
            errores.append("'%s'='%s' no esta en %s" % (campo, v, regla["valores"]))
    return errores

def llamar_validado(pr, intentos=3, modelo=MODELO, temperatura=0.7, esquema=ESQUEMA):
    """Patron completo: llamar -> validar -> reintentar con el error -> rechazar."""
    ultimo_error = None
    for i in range(1, intentos + 1):
        texto_extra = "" if not ultimo_error else (
            "\n\nTu respuesta anterior fue invalida: " + "; ".join(ultimo_error) +
            "\nCorrigela y responde SOLO el JSON.")
        r = chat(pr + texto_extra, modelo=modelo, temperature=temperatura)
        try:
            d = r.json()
        except Exception:
            ultimo_error = ["la respuesta no era JSON parseable"]
            continue
        errores = validar(d, esquema)
        if not errores:
            return {"estado": "ok", "datos": d, "intentos": i}
        ultimo_error = errores
    return {"estado": "rechazado", "error": ultimo_error, "intentos": intentos}

resultados = [llamar_validado(prompt_flojo) for _ in range(10)]
print("ok:", sum(1 for r in resultados if r["estado"] == "ok"),
      "| rechazados:", sum(1 for r in resultados if r["estado"] == "rechazado"),
      "| intentos medios:", round(statistics.mean(r["intentos"] for r in resultados), 2))
print("\nRechazo controlado: pedimos un campo que el modelo nunca devuelve.")
ESQUEMA_EXIGENTE = dict(ESQUEMA)
ESQUEMA_EXIGENTE["impacto_negocio"] = {"tipo": str, "obligatorio": True}
print(llamar_validado(prompt_flojo, esquema=ESQUEMA_EXIGENTE))

# %% [markdown]
# ### EJERCICIO 2
#
# Anade al `ESQUEMA` el campo `confianza`: numero entre 0 y 1, obligatorio.
# Tendras que extender `validar()` para soportar rangos (`minimo`/`maximo`).
# Vuelve a correr y mira como cambia la tasa de rechazo.
#
# > Pregunta para el equipo: en tu sistema real, **que hace tu codigo hoy** cuando
# > el JSON viene mal? Si la respuesta es "peta", ya tienes tu primera tarea.

# %%
# TODO: tu version extendida
ESQUEMA_V2 = dict(ESQUEMA)
# ESQUEMA_V2["confianza"] = {"tipo": float, "minimo": 0.0, "maximo": 1.0, "obligatorio": True}

print("campos del esquema:", list(ESQUEMA_V2))
print("OK" if "confianza" in ESQUEMA_V2 else "Todavia falta 'confianza' en ESQUEMA_V2.")

# %% [markdown]
# ---
# ## 4. El contexto es un escritorio, no una memoria
#
# Cada llamada empieza con el escritorio vacio y **pagas entero** lo que pongas encima.
# Vamos a desglosar de que esta hecho tu contexto.

# %%
partes = {
    "1. instrucciones (fijo)": p["plantilla"].split("Ticket:")[0],
    "2. ejemplos (fijo)":      L.cargar_prompt("clasificar_incidente.v2.yaml")["plantilla"].split("Ejemplo 1")[1].split("Responde")[0],
    "3. documento recuperado": runbook,
    "4. historial (crece)":    ("usuario: hola\nasistente: hola, en que ayudo\n" * 12),
    "5. la peticion real":     TICKET,
}
filas = []
total = 0
for nombre, txt in partes.items():
    t = contar_tokens(txt)
    total += t
    filas.append({"parte": nombre, "tokens": t})
for f in filas:
    f["% del total"] = "%.1f%%" % (100 * f["tokens"] / total)
tabla(filas)
print("\nTotal de entrada: %d tokens | costo de 1000 llamadas asi: %.2f USD"
      % (total, L.costo_usd(MODELO, total, 60) * 1000))
print("La peticion real es el %.1f%% del total. Todo lo demas es escritorio."
      % (100 * contar_tokens(TICKET) / total))

# %% [markdown]
# ### EJERCICIO 3
#
# Poda el contexto: quedate solo con las partes 1 y 5, y con los **300 tokens del
# runbook mas relevantes** para el ticket (pista: parte el documento por titulos `##`
# y quedate con el fragmento que comparte mas palabras con el ticket).
# Calcula el ahorro por cada 1000 llamadas.

# %%
def fragmento_relevante(doc, consulta, max_tokens=300):
    # TODO: parte `doc` por secciones que empiezan con "## ", puntua cada seccion por
    #       numero de palabras compartidas con `consulta` y devuelve la mejor,
    #       recortada a max_tokens.
    secciones = [s for s in doc.split("## ") if s.strip()]
    ...
    return doc          # <-- sin podar: devuelve el documento entero

antes = total
despues = contar_tokens(partes["1. instrucciones (fijo)"]) + contar_tokens(TICKET) + \
          contar_tokens(fragmento_relevante(runbook, TICKET))
ahorro = 100 * (1 - despues / antes)
print("antes: %d tokens | despues: %d tokens | ahorro: %.0f%%" % (antes, despues, ahorro))
print("OK" if ahorro > 50 else "El ahorro es bajo: todavia estas mandando el documento entero.")

# %% [markdown]
# ---
# ## 5. Loop engineering: un bucle sin frenos factura toda la noche
#
# `Razonar -> Actuar -> Observar -> repetir`. Los cuatro fallos de la slide son:
# parada temprana, bucle infinito, agotamiento de contexto e incoherencia larga.
# Aqui construimos el bucle **con** sus frenos y luego se los quitamos.

# %%
# Herramientas de juguete (deterministas, para ver el bucle, no el modelo)
ESTADO_SISTEMA = {"pods_reiniciados": 0}

def buscar_logs(servicio):
    return "OOMKilled x3 en %s" % servicio

def reiniciar_pod(servicio):
    ESTADO_SISTEMA["pods_reiniciados"] += 1
    return "pod de %s reiniciado" % servicio

HERRAMIENTAS = {"buscar_logs": buscar_logs, "reiniciar_pod": reiniciar_pod}

def bucle(plan, max_pasos=10, max_tokens_total=4000, detectar_repeticion=True):
    """Un harness minimo. `plan` simula lo que decidiria el modelo en cada vuelta."""
    estado = {"pasos": 0, "tokens": 0, "historial": [], "parada": None}
    vistos = set()
    while True:
        if estado["pasos"] >= max_pasos:
            estado["parada"] = "tope de pasos"; break
        if estado["tokens"] >= max_tokens_total:
            estado["parada"] = "tope de tokens"; break
        accion = plan(estado)
        if accion is None:
            estado["parada"] = "tarea completada"; break
        firma = (accion["herramienta"], accion["argumento"])
        if detectar_repeticion and firma in vistos:
            estado["parada"] = "repeticion detectada: %s" % (firma,); break
        vistos.add(firma)
        obs = HERRAMIENTAS[accion["herramienta"]](accion["argumento"])
        estado["pasos"] += 1
        estado["tokens"] += 120 + len(obs)
        estado["historial"].append((accion["herramienta"], obs))
    return estado

# Un "modelo" que se atasca: siempre quiere reiniciar el mismo pod
def plan_atascado(estado):
    return {"herramienta": "reiniciar_pod", "argumento": "pagos-api"}

print("CON frenos: ", bucle(plan_atascado)["parada"])
print("SIN deteccion de repeticion:", bucle(plan_atascado, detectar_repeticion=False)["parada"],
      "| pods reiniciados:", ESTADO_SISTEMA["pods_reiniciados"])

# %% [markdown]
# ### EJERCICIO 4
#
# 1. Sube `max_pasos` a 500 con `detectar_repeticion=False` y mira el contador de
#    `pods_reiniciados`. Eso, en produccion, es un incidente.
# 2. Escribe un `plan_bueno(estado)` que: busque logs, reinicie el pod y **devuelva
#    `None`** (criterio de terminacion explicito). Comprueba que para por
#    "tarea completada" y no por un tope.

# %%
def plan_bueno(estado):
    # TODO: paso 0 -> buscar_logs, paso 1 -> reiniciar_pod, paso 2 -> None (terminar)
    ...

res = bucle(plan_bueno)
print("parada:", res["parada"], "| pasos dados:", len(res["historial"]))
print("OK" if len(res["historial"]) == 2 and res["parada"] == "tarea completada"
      else "Todavia no: deberia dar 2 pasos y parar por 'tarea completada'.")

# %% [markdown]
# ---
# ## 6. Graph engineering: estado, nodos y aristas condicionales
#
# Cuando un bucle ya no alcanza: el estado sale del contexto y vive en un objeto
# tipado; cada paso es un nodo; el control de flujo son aristas condicionales.
# **El fallo se vuelve localizable.**
#
# (Esto es LangGraph en 40 lineas, sin instalar LangGraph.)

# %%
from dataclasses import dataclass, field

@dataclass
class Estado:
    ticket: str
    clasificacion: dict = field(default_factory=dict)
    errores: list = field(default_factory=list)
    intentos: int = 0
    aprobado: bool = False
    recorrido: list = field(default_factory=list)

def nodo_clasificar(s: Estado) -> Estado:
    s.intentos += 1
    r = chat(L.render(p["plantilla"], ticket=s.ticket), modelo=MODELO, temperature=0.7)
    try:
        s.clasificacion = r.json(); s.errores = validar(s.clasificacion)
    except Exception as e:
        s.clasificacion, s.errores = {}, ["no parseable: %s" % e]
    return s

def nodo_enriquecer(s: Estado) -> Estado:
    s.clasificacion["sla_minutos"] = {"critica": 15, "alta": 60, "media": 240, "baja": 1440}[
        s.clasificacion["severidad"]]
    return s

def nodo_aprobacion_humana(s: Estado) -> Estado:
    # En produccion aqui se PAUSA el grafo y se persiste el estado.
    s.aprobado = True     # simulamos que la persona aprueba
    return s

def nodo_cerrar(s: Estado) -> Estado:
    return s

# Aristas condicionales: son tus clausulas de guarda
def ruta_tras_clasificar(s: Estado) -> str:
    if s.errores and s.intentos < 3:
        return "clasificar"            # ciclo de reintento
    if s.errores:
        return "cerrar"                # nos rendimos de forma controlada
    return "enriquecer"

def ruta_tras_enriquecer(s: Estado) -> str:
    return "aprobacion_humana" if s.clasificacion.get("requiere_humano") else "cerrar"

GRAFO = {
    "clasificar":        (nodo_clasificar, ruta_tras_clasificar),
    "enriquecer":        (nodo_enriquecer, ruta_tras_enriquecer),
    "aprobacion_humana": (nodo_aprobacion_humana, lambda s: "cerrar"),
    "cerrar":            (nodo_cerrar, lambda s: None),
}

def ejecutar(estado: Estado, inicio="clasificar", max_nodos=12):
    actual = inicio
    while actual and len(estado.recorrido) < max_nodos:
        fn, ruta = GRAFO[actual]
        estado.recorrido.append(actual)
        estado = fn(estado)
        actual = ruta(estado)
    return estado

s = ejecutar(Estado(ticket=TICKET))
print("recorrido:", " -> ".join(s.recorrido))
print("clasificacion:", s.clasificacion)
print("errores:", s.errores, "| intentos:", s.intentos, "| aprobado:", s.aprobado)

s2 = ejecutar(Estado(ticket="Detectamos una clave expuesta de AWS en un repositorio publico. servicio: infra-core. Brecha activa."))
print("\nrecorrido (caso de seguridad):", " -> ".join(s2.recorrido))

# %% [markdown]
# ### EJERCICIO 5
#
# 1. Anade un nodo `notificar` que solo se ejecute si `severidad == "critica"`,
#    entre `enriquecer` y `cerrar`. Tendras que tocar **solo** `ruta_tras_enriquecer`
#    y el diccionario `GRAFO`: eso es exactamente la ventaja del grafo.
# 2. Haz que `nodo_aprobacion_humana` rechace si `confianza < 0.5` y vuelva a
#    `clasificar`. Comprueba que el tope `max_nodos` te salva de un ciclo infinito.
#
# > Compara con el ejercicio 4: en el bucle, cuando algo falla sabes que "fallo el
# > agente". En el grafo sabes **que nodo**, con que entrada y que quedo bloqueado.

# %% [markdown]
# ---
# ## 7. El gateway y el ruteo en cascada
#
# Regla de la sesion: **ninguna parte del codigo llama al proveedor directamente**.
# Todo pasa por un punto unico. Y una vez que existe ese punto, puedes rutear:
# el modelo pequeno atiende lo facil, el grande solo ve lo que el pequeno no pudo.

# %%
L.limpiar_trazas()
casos = L.cargar_golden()
plantilla_v2 = L.cargar_prompt("clasificar_incidente.v2.yaml")["plantilla"]

def gateway(ticket, estrategia="cascada", umbral=0.75):
    """Punto unico de salida. Aqui viven ruteo, registro y (mas adelante) cache y fallback."""
    pr = L.render(plantilla_v2, ticket=ticket)
    if estrategia == "solo_pequeno":
        r = chat(pr, modelo="sim-small", formato_json=True, prompt_id="clasificar:v2")
        return r.json(), r.costo_usd, "sim-small"
    if estrategia == "solo_grande":
        r = chat(pr, modelo="sim-large", formato_json=True, prompt_id="clasificar:v2")
        return r.json(), r.costo_usd, "sim-large"
    # cascada
    r = chat(pr, modelo="sim-small", formato_json=True, prompt_id="clasificar:v2")
    d, costo = r.json(), r.costo_usd
    if d.get("confianza", 0) >= umbral:
        return d, costo, "sim-small"
    r2 = chat(pr, modelo="sim-large", formato_json=True, prompt_id="clasificar:v2")
    return r2.json(), costo + r2.costo_usd, "sim-large"

def evaluar(estrategia, umbral=0.75):
    ok = costo = 0.0
    escalados = 0
    for c in casos:
        d, cst, modelo_usado = gateway(c["entrada"], estrategia, umbral)
        ok += d.get("categoria") == c["esperado"]["categoria"]
        costo += cst
        escalados += modelo_usado == "sim-large"
    return {"estrategia": estrategia + ("" if estrategia != "cascada" else " (umbral %.2f)" % umbral),
            "exactitud": round(ok / len(casos), 3),
            "costo_1000_req_usd": round(costo / len(casos) * 1000, 3),
            "% al modelo grande": "%.0f%%" % (100 * escalados / len(casos))}

tabla([evaluar("solo_pequeno"), evaluar("solo_grande"), evaluar("cascada", 0.75)])

# %% [markdown]
# ### EJERCICIO 6
#
# Encuentra el **umbral optimo**: el que mantiene la exactitud del modelo grande
# gastando lo menos posible. Corre la celda y decide con la tabla, no con la intuicion.
#
# Trampa comun de la slide: *un router mal calibrado ahorra dinero y pierde clientes*.
# Por eso la tabla trae siempre las dos columnas juntas.

# %%
tabla([evaluar("cascada", u) for u in (0.50, 0.65, 0.75, 0.85, 0.95)])
# TODO: escribe aqui abajo el umbral que elegirias para TU caso y por que.
DECISION = "umbral = ?  porque ..."

# %%
# El gateway registra todo. Esto es el embrion del esquema de trazas de la Sesion 3.
print(json.dumps(L.resumen_trazas(), indent=2))
print("\nUna traza tiene estos campos:")
print(json.dumps(L.TRAZAS[0], indent=2, ensure_ascii=False)[:700])

# %% [markdown]
# ---
# ## Cierre
#
# Lo que acabas de construir a mano, en orden:
#
# 1. una llamada con **instruccion de honestidad** (contra la invencion)
# 2. una medida de **variacion** y un voto por mayoria
# 3. **validacion de esquema + reintento + rechazo controlado**
# 4. un **presupuesto de contexto** en tokens y en dolares
# 5. un **bucle con frenos** (pasos, tokens, repeticion, terminacion explicita)
# 6. un **grafo** con estado, ciclo de reintento y punto de aprobacion humana
# 7. un **gateway** con ruteo en cascada, medido en exactitud y en costo
#
# ### Tarea entre sesiones
#
# Trae **20 a 30 ejemplos reales** de tu caso de uso con la respuesta correcta
# esperada. Formato sugerido (una linea por caso, archivo `.jsonl`):
#
# ```json
# {"id": "CASO-001", "entrada": "...", "esperado": {...}, "dificultad": "tipico"}
# ```
#
# Composicion: **60% tipicos, 30% dificiles, 10% que deben rechazarse**.
# Con eso empieza la Sesion 2.
