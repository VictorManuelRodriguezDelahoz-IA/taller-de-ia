# %% [markdown]
# # Sesion 4 - Costo, latencia y resiliencia
#
# **Taller AI DevOps - ClickIT** | Laboratorio de la sesion 4
#
# Objetivo: **costo por cliente instrumentado, cache funcionando y un fallback probado**.
#
# | # | Idea de la sesion | Lo que haras aqui |
# |---|---|---|
# | 1 | Unidades de costo | Repartir el gasto por request, por tarea y por tenant |
# | 2 | Controles duros | Cortar automaticamente, no solo alertar |
# | 3 | Cache exacta | Medir el acierto real y provocar la fuga entre usuarios |
# | 4 | Cache de prefijo | Reordenar el prompt y ver bajar los tokens facturados |
# | 5 | Cache semantica | Ver como un umbral flojo devuelve la respuesta de otra pregunta |
# | 6 | Presupuesto de latencia | Repartirlo y medir el p95, no el promedio |
# | 7 | Resiliencia | Reintentos, timeout, corta-circuitos, fallback y degradacion |
# | 8 | La regla de oro | Volver a correr el eval: si el puntaje bajo, no hubo ahorro |

# %%
import sys, json, time, random, hashlib, math
from pathlib import Path
from collections import defaultdict, Counter

RAIZ = Path.cwd()
if not (RAIZ / "lab_utils.py").exists():
    RAIZ = RAIZ.parent
sys.path.insert(0, str(RAIZ))

import lab_utils as L
from lab_utils import chat, tabla, barra, ProveedorError
from evaluador import correr_eval

CASOS = L.cargar_golden()
P2 = L.cargar_prompt("clasificar_incidente.v2.yaml")
print("Precios del simulador (USD por millon de tokens):", L.PRECIOS)

# %% [markdown]
# ---
# ## 1. Unidades de costo que sirven para decidir
#
# La factura mensual no explica nada. Estas cinco unidades si:
# por request, por **tarea resuelta**, por usuario activo, por **tenant** y por feature.
#
# Simulamos un dia de trafico con tres clientes.

# %%
L.limpiar_trazas()
random.seed(11)
TENANTS = {"acme": 0.55, "globex": 0.30, "initech": 0.15}

def atender(ticket, tenant, feature="clasificacion"):
    r = chat(L.render(P2["plantilla"], ticket=ticket), modelo="sim-small",
             formato_json=True, prompt_id="clasificar:v2", tenant=tenant)
    L.TRAZAS[-1]["feature"] = feature
    try:
        return r.json(), True
    except Exception:
        return {}, False

for _ in range(150):
    tenant = random.choices(list(TENANTS), weights=list(TENANTS.values()))[0]
    caso = random.choice(CASOS)
    # initech manda tickets enormes: es el que se come el margen de todos
    entrada = caso["entrada"] + (" " + L.documento("runbook_incidentes.md") * 4 if tenant == "initech" else "")
    atender(entrada, tenant)

por_tenant = defaultdict(lambda: {"requests": 0, "costo": 0.0, "tokens": 0})
for t in L.TRAZAS:
    d = por_tenant[t["tenant"]]
    d["requests"] += 1
    d["costo"] += t["costo_usd"]
    d["tokens"] += t["tokens_in"] + t["tokens_out"]

total = sum(d["costo"] for d in por_tenant.values())
tabla([{"tenant": k, "requests": d["requests"], "costo_usd": round(d["costo"], 5),
        "% del gasto": "%.0f%%" % (100 * d["costo"] / total),
        "costo_por_request": round(d["costo"] / d["requests"], 6),
        "": barra(d["costo"] / total, 18)}
       for k, d in sorted(por_tenant.items(), key=lambda kv: -kv[1]["costo"])])
print("\ncosto total del dia simulado: %.4f USD" % total)

# %% [markdown]
# ### EJERCICIO 1
#
# `costo_por_request` es diagnostico tecnico. La unidad de negocio es
# **costo por tarea resuelta**: incluye los reintentos y el tiempo humano de revision.
#
# Calculalo: cuenta una tarea como resuelta solo si la salida fue valida, y suma
# **0,40 USD** por cada tarea que acabo en revision humana (`requiere_humano`).

# %%
def costo_por_tarea_resuelta(trazas, tareas_ok, tareas_a_humano, coste_humano=0.40):
    # TODO: (costo de modelo + coste humano total) / tareas resueltas
    ...

# %% [markdown]
# ---
# ## 2. Controles duros: cortar, no avisar
#
# *"La alerta sola no ha frenado nunca nada."* Alerta al 80%, corte al 100%.

# %%
class Presupuesto:
    def __init__(self, tope_usd, alerta=0.8):
        self.tope, self.alerta, self.gastado, self.avisado = tope_usd, alerta, 0.0, False

    def cobrar(self, usd):
        if self.gastado + usd > self.tope:
            raise RuntimeError("presupuesto agotado: %.4f de %.4f USD" % (self.gastado, self.tope))
        self.gastado += usd
        if not self.avisado and self.gastado > self.tope * self.alerta:
            self.avisado = True
            print("   AVISO: %.0f%% del presupuesto consumido" % (100 * self.gastado / self.tope))

pres = Presupuesto(tope_usd=0.0025)
cortado = 0
for i, caso in enumerate(CASOS, 1):
    r = chat(L.render(P2["plantilla"], ticket=caso["entrada"]), modelo="sim-small",
             formato_json=True, registrar=False)
    try:
        pres.cobrar(r.costo_usd)
    except RuntimeError as e:
        cortado = i
        print("   CORTE en el request %d: %s" % (i, e))
        break
print("Peticiones atendidas antes del corte:", cortado - 1 if cortado else len(CASOS))
print("En produccion el corte devuelve un error tipado y el flujo cae a la ruta manual.")

# %% [markdown]
# ---
# ## 3. Cache exacta: barata, trivial... y peligrosa si la clave esta mal
#
# La clave incluye **modelo + version de prompt + ambito de permisos**. Siempre.
# Si te dejas el ambito, el usuario A recibe la respuesta calculada para el usuario B.

# %%
class CacheExacta:
    def __init__(self, ttl_s=3600, incluir_ambito=True):
        self.datos, self.ttl, self.incluir_ambito = {}, ttl_s, incluir_ambito
        self.aciertos = self.fallos = 0

    def clave(self, prompt, modelo, prompt_id, ambito):
        partes = [modelo, prompt_id, prompt]
        if self.incluir_ambito:
            partes.append(ambito)
        return hashlib.sha256("|".join(partes).encode()).hexdigest()

    def obtener(self, *args):
        k = self.clave(*args)
        e = self.datos.get(k)
        if e and time.time() - e[1] < self.ttl:
            self.aciertos += 1
            return e[0]
        self.fallos += 1
        return None

    def guardar(self, valor, *args):
        self.datos[self.clave(*args)] = (valor, time.time())

    @property
    def tasa_acierto(self):
        tot = self.aciertos + self.fallos
        return self.aciertos / tot if tot else 0.0

def con_cache(ticket, cache, ambito="tenant:acme|rol:soporte"):
    pr = L.render(P2["plantilla"], ticket=ticket)
    hit = cache.obtener(pr, "sim-small", "clasificar:v2", ambito)
    if hit is not None:
        return hit, 0.0
    r = chat(pr, modelo="sim-small", formato_json=True, prompt_id="clasificar:v2", registrar=False)
    cache.guardar(r.texto, pr, "sim-small", "clasificar:v2", ambito)
    return r.texto, r.costo_usd

# Trafico realista: unos pocos tickets se repiten mucho
random.seed(3)
trafico = [random.choice(CASOS[:8])["entrada"] for _ in range(80)] + \
          [random.choice(CASOS)["entrada"] for _ in range(40)]

cache = CacheExacta()
costo = sum(con_cache(t, cache)[1] for t in trafico)
sin_cache = sum(chat(L.render(P2["plantilla"], ticket=t), modelo="sim-small",
                     formato_json=True, registrar=False).costo_usd for t in trafico)
print("tasa de acierto real: %.0f%%" % (100 * cache.tasa_acierto))
print("costo sin cache: %.5f USD | con cache: %.5f USD | ahorro: %.0f%%"
      % (sin_cache, costo, 100 * (1 - costo / sin_cache)))

# %% [markdown]
# ### La fuga de datos con otro nombre

# %%
mala = CacheExacta(incluir_ambito=False)
ticket_confidencial = "Revisa el expediente del cliente ACME. servicio: facturacion"
r_acme, _ = con_cache(ticket_confidencial, mala, ambito="tenant:acme|rol:admin")
r_globex, _ = con_cache(ticket_confidencial, mala, ambito="tenant:globex|rol:lectura")
print("acme  ->", r_acme[:90])
print("globex->", r_globex[:90])
print("misma respuesta servida a otro tenant:", r_acme == r_globex, " <- esto es una fuga")

print("(el texto puede coincidir porque el modelo es determinista; lo grave es que")
print(" globex leyo una entrada calculada bajo los permisos de acme)")

buena = CacheExacta(incluir_ambito=True)
con_cache(ticket_confidencial, buena, ambito="tenant:acme|rol:admin")
con_cache(ticket_confidencial, buena, ambito="tenant:globex|rol:lectura")
print("")
print("SIN ambito en la clave: aciertos=%d fallos=%d -> el segundo tenant leyo la cache del primero"
      % (mala.aciertos, mala.fallos))
print("CON ambito en la clave: aciertos=%d fallos=%d -> cada tenant tiene su entrada"
      % (buena.aciertos, buena.fallos))

# %% [markdown]
# ### EJERCICIO 2
#
# 1. Anade `invalidar(prompt_id)` para tirar la cache cuando despliegas una version
#    nueva del prompt. Sin eso, el rollback de la Sesion 3 deja respuestas viejas vivas.
# 2. Define **que NUNCA se cachea**: escribe `no_cachear(ticket, ambito)` que devuelva
#    True para todo lo que dependa de permisos del usuario o contenga datos personales.
#
# ---
# ## 4. Cache de prefijo: por que el orden del prompt es dinero
#
# El proveedor cachea la parte **estable** del principio del prompt. Si pones lo
# variable arriba, no cacheas nada. Los tokens cacheados se facturan a una fraccion.

# %%
DESCUENTO_CACHE = 0.10       # los tokens cacheados cuestan ~10% (verifica el tuyo)

def facturar(prompt, prefijos_vistos):
    """Simula la facturacion con cache de prefijo del proveedor."""
    tokens = L.contar_tokens(prompt)
    cacheados = 0
    for pref in prefijos_vistos:
        comun = 0
        for a, b in zip(prompt, pref):
            if a != b:
                break
            comun += 1
        cacheados = max(cacheados, L.contar_tokens(prompt[:comun]))
    prefijos_vistos.add(prompt)
    facturables = (tokens - cacheados) + cacheados * DESCUENTO_CACHE
    return tokens, cacheados, facturables

INSTRUCCIONES = P2["plantilla"].split("Ticket:")[0]

def prompt_bien_ordenado(ticket):
    return INSTRUCCIONES + "Ticket: " + ticket        # lo fijo primero, lo variable al final

def prompt_mal_ordenado(ticket):
    return "Ticket: " + ticket + chr(10) * 2 + INSTRUCCIONES

for nombre, constructor in (("lo variable arriba (mal)", prompt_mal_ordenado),
                            ("lo fijo arriba (bien)", prompt_bien_ordenado)):
    vistos, tot, fact = set(), 0, 0.0
    for c in CASOS:
        t, cach, f = facturar(constructor(c["entrada"]), vistos)
        tot += t; fact += f
    print("%-26s tokens reales %6d | facturados %8.0f | ahorro %.0f%%"
          % (nombre, tot, fact, 100 * (1 - fact / tot)))

# %% [markdown]
# ---
# ## 5. Cache semantica: potente y peligrosa
#
# Recupera respuestas de preguntas **parecidas**. Por debajo de 0,95 de similitud
# empieza a devolver la respuesta de otra pregunta.

# %%
def vectorizar(texto):
    return Counter(w for w in L._norm(texto).split() if len(w) > 3)

def similitud(a, b):
    va, vb = vectorizar(a), vectorizar(b)
    comunes = set(va) & set(vb)
    num = sum(va[w] * vb[w] for w in comunes)
    den = math.sqrt(sum(v * v for v in va.values())) * math.sqrt(sum(v * v for v in vb.values()))
    return num / den if den else 0.0

class CacheSemantica:
    def __init__(self, umbral=0.95):
        self.umbral, self.entradas = umbral, []

    def obtener(self, ticket):
        mejor, origen, mejor_s = None, None, 0.0
        for texto, resp in self.entradas:
            s = similitud(ticket, texto)
            if s > mejor_s:
                mejor, origen, mejor_s = resp, texto, s
        if mejor_s >= self.umbral:
            return mejor, origen, mejor_s
        return None, origen, mejor_s

    def guardar(self, ticket, resp):
        self.entradas.append((ticket, resp))

pregunta_1 = "El backup automatico no se ejecuta desde el martes. servicio: pedidos-db"
pregunta_2 = "El backup automatico no se ejecuta desde el martes. servicio: crm-db"

for umbral in (0.80, 0.95):
    cs = CacheSemantica(umbral)
    r1 = chat(L.render(P2["plantilla"], ticket=pregunta_1), modelo="sim-small",
              formato_json=True, registrar=False).texto
    cs.guardar(pregunta_1, r1)
    hit, origen, s = cs.obtener(pregunta_2)
    print("umbral %.2f -> similitud %.3f | %s" % (umbral, s,
          "ACIERTO (devuelve la respuesta de la otra pregunta)" if hit else "fallo de cache (correcto)"))
    if hit:
        print("   servida:", hit[:100])
        print("   pero el ticket preguntaba por otro servicio y otro riesgo.")

# %% [markdown]
# ### EJERCICIO 3
#
# Mide el **coste del error**: corre el set dorado con cache semantica a 0,80 y a 0,95
# y compara la tasa de acierto con la caida de puntaje. Vas a ver por que el umbral
# flojo "ahorra" y rompe.
#
# ---
# ## 6. Presupuesto de latencia
#
# Se reparte **antes** de optimizar. Y se mide el p95, no el promedio: el promedio
# esconde exactamente los casos que hacen que un usuario abandone.

# %%
PRESUPUESTO = [("recuperacion de contexto", 150), ("primera llamada al modelo", 800),
               ("llamadas a herramientas", 400), ("validacion y post-proceso", 100),
               ("reserva para reintento", 550)]
tabla([{"paso": p, "ms": ms, "": barra(ms / 2000, 24)} for p, ms in PRESUPUESTO])
print("total: %d ms" % sum(ms for _, ms in PRESUPUESTO))

L.limpiar_trazas()
for c in CASOS:
    chat(L.render(P2["plantilla"], ticket=c["entrada"]), modelo="sim-small", formato_json=True)
lat = sorted(t["latencia_ms"] for t in L.TRAZAS)
promedio = sum(lat) / len(lat)
p95 = lat[int(len(lat) * 0.95) - 1]
print("\npromedio %d ms | p95 %d ms | maximo %d ms" % (promedio, p95, lat[-1]))
print("el p95 es %.1fx el promedio: por eso no se alerta sobre el promedio" % (p95 / promedio))

# %% [markdown]
# ### EJERCICIO 4
#
# Con tu p95 real, calcula el **timeout** que dice la slide (`p95 x 2`) y comprueba
# cuantas peticiones moririan con ese timeout. Luego pruebalo de verdad:
# `chat(..., timeout_s=...)` lanza `TimeoutError` cuando la llamada no cabe.

# %%
timeout = (p95 * 2) / 1000.0
muertas = ok = 0
for c in CASOS[:20]:
    try:
        chat(L.render(P2["plantilla"], ticket=c["entrada"]), modelo="sim-small",
             formato_json=True, timeout_s=timeout, registrar=False)
        ok += 1
    except TimeoutError:
        muertas += 1
print("timeout = %.2f s (p95 x 2) -> %d ok, %d cortadas por timeout" % (timeout, ok, muertas))

apretado = (p95 * 0.8) / 1000.0
muertas2 = 0
for c in CASOS[:20]:
    try:
        chat(L.render(P2["plantilla"], ticket=c["entrada"]), modelo="sim-small",
             formato_json=True, timeout_s=apretado, registrar=False)
    except TimeoutError:
        muertas2 += 1
print("timeout = %.2f s (demasiado justo) -> %d cortadas de 20" % (apretado, muertas2))
print("Un timeout por debajo del p95 convierte lentitud en errores para el usuario.")

# %% [markdown]
# ---
# ## 7. Que pasa cuando el proveedor falla
#
# Los seis controles de la slide, uno por uno. `L.configurar_fallos()` apaga el
# proveedor a voluntad: **la prueba de fuego es apagarlo en horario laboral y mirar
# que ve el usuario**.

# %%
class CircuitoAbierto(RuntimeError):
    pass

class CortaCircuitos:
    def __init__(self, fallos=5, ventana_s=30):
        self.limite, self.ventana, self.fallos, self.abierto_hasta = fallos, ventana_s, 0, 0

    def antes(self):
        if time.time() < self.abierto_hasta:
            raise CircuitoAbierto("circuito abierto, faltan %.1f s"
                                  % (self.abierto_hasta - time.time()))

    def registrar(self, ok):
        if ok:
            self.fallos = 0
        else:
            self.fallos += 1
            if self.fallos >= self.limite:
                self.abierto_hasta = time.time() + self.ventana
                self.fallos = 0
                print("   corta-circuitos ABIERTO %d s" % self.ventana)

BREAKERS = defaultdict(lambda: CortaCircuitos(fallos=3, ventana_s=2))

def gateway_resiliente(ticket, modelos=("sim-small", "sim-large"), intentos=3,
                       timeout_s=3.0, degradar=True):
    """Reintentos con espera exponencial + jitter, timeout, corta-circuitos,
    fallback entre modelos y degradacion elegante. En ese orden."""
    pr = L.render(P2["plantilla"], ticket=ticket)
    for modelo in modelos:
        for intento in range(1, intentos + 1):
            try:
                BREAKERS[modelo].antes()
                r = chat(pr, modelo=modelo, formato_json=True, timeout_s=timeout_s,
                         prompt_id="clasificar:v2", registrar=False)
                BREAKERS[modelo].registrar(True)
                return {"estado": "ok", "modelo": modelo, "intentos": intento,
                        "salida": r.json()}
            except CircuitoAbierto:
                break                                   # ni lo intentes: pasa al fallback
            except (L.ProveedorError, TimeoutError):
                BREAKERS[modelo].registrar(False)
                espera = (0.2 * (2 ** (intento - 1))) + random.uniform(0, 0.1)
                time.sleep(min(espera, 0.5) * L.VELOCIDAD_SIM * 20)
    if degradar:
        return {"estado": "degradado", "modelo": None, "intentos": intentos,
                "salida": {"categoria": "sin_clasificar", "severidad": "media",
                           "requiere_humano": True, "nota": "cola manual"}}
    raise L.ProveedorError("todos los proveedores fallaron")

print("A) proveedor principal caido, fallback disponible")
L.configurar_fallos(probabilidad=1.0, modelos=["sim-small"])
print("   ", gateway_resiliente(CASOS[0]["entrada"]))

print("\nB) todo el proveedor caido -> degradacion elegante")
L.configurar_fallos(probabilidad=1.0)
print("   ", gateway_resiliente(CASOS[0]["entrada"]))

print("\nC) fallos intermitentes (30%) -> los reintentos absorben")
L.configurar_fallos(probabilidad=0.3)
BREAKERS.clear()          # el circuito se cierra solo tras su ventana; aqui lo reseteamos
res = [gateway_resiliente(c["entrada"]) for c in CASOS[:15]]
print("   ok:", sum(1 for r in res if r["estado"] == "ok"),
      "| degradados:", sum(1 for r in res if r["estado"] == "degradado"),
      "| intentos medios: %.2f" % (sum(r["intentos"] for r in res) / len(res)))
L.configurar_fallos(0.0)
print("\nproveedor restaurado")

# %% [markdown]
# ### EJERCICIO 5
#
# 1. **Fallos parciales en agentes**: si el paso 4 de 7 falla, hay que decidir ANTES
#    entre reintentar el paso, reiniciar todo o entregar parcial. Implementa la
#    politica `reintentar_paso` sobre el grafo de la Sesion 1.
# 2. Escribe la **prueba de fuego**: apaga el proveedor con `L.configurar_fallos(1.0)`
#    mientras corre un lote y comprueba que el usuario nunca ve una excepcion cruda.

# %% [markdown]
# ---
# ## 8. La regla de oro: un ahorro sin eval no es un ahorro
#
# *"Volver a correr el eval: costo, latencia y puntaje. Si el puntaje bajo, el ahorro
# no cuenta."* Comparamos tres configuraciones **con el mismo set dorado**.

# %%
cache_final = CacheExacta()

def gateway_optimizado(ticket, prompt_dict):
    pr = L.render(prompt_dict["plantilla"], ticket=ticket)
    hit = cache_final.obtener(pr, "sim-small", "clasificar:v2", "tenant:eval")
    if hit is not None:
        try:
            return json.loads(L.extraer_json(hit)), 0.0
        except Exception:
            return None, 0.0
    r = chat(pr, modelo="sim-small", formato_json=True, prompt_id="clasificar:v2")
    cache_final.guardar(r.texto, pr, "sim-small", "clasificar:v2", "tenant:eval")
    try:
        return r.json(), r.costo_usd
    except Exception:
        return None, r.costo_usd

def gateway_agresivo(ticket, prompt_dict):
    """Recorta el prompt a la mitad para ahorrar. Parece buena idea."""
    corto = prompt_dict["plantilla"].split("Rubrica")[0] + "\n\nTicket: {{ticket}}"
    r = chat(L.render(corto, ticket=ticket), modelo="sim-small", formato_json=True,
             prompt_id="clasificar:recortado")
    try:
        return r.json(), r.costo_usd
    except Exception:
        return None, r.costo_usd

base      = correr_eval("clasificar_incidente.v2.yaml", runs_por_caso=2, etiqueta="base")
con_cache_= correr_eval("clasificar_incidente.v2.yaml", runs_por_caso=2, etiqueta="con cache exacta",
                        gateway=gateway_optimizado)
agresivo  = correr_eval("clasificar_incidente.v2.yaml", runs_por_caso=2, etiqueta="prompt recortado",
                        gateway=gateway_agresivo)

tabla([{"configuracion": r["etiqueta"], "score": r["score_global"],
        "costo/caso_usd": r["costo_por_caso_usd"], "p95_ms": r["latencia_p95_ms"],
        "veredicto": "OK" if r["score_global"] >= base["score_global"] - 0.02 else "DEGRADA"}
       for r in (base, con_cache_, agresivo)])
print("\ntasa de acierto de la cache durante el eval: %.0f%%" % (100 * cache_final.tasa_acierto))
print("\nEl recorte del prompt ahorra, pero fijate en la columna de puntaje antes de")
print("celebrarlo. Un ahorro que no se valida es una degradacion que aun no se ha notado.")

# %% [markdown]
# ---
# ## Cierre
#
# Te llevas: costo por tenant, un presupuesto que corta, tres capas de cache con sus
# trampas, un presupuesto de latencia medido en p95 y un gateway resiliente con
# fallback probado y degradacion elegante.
#
# ### Valores de referencia de la sesion (punto de partida, se corrigen con tu telemetria)
#
# | control | valor |
# |---|---|
# | reintentos | maximo 3, espera 200/400/800 ms + jitter |
# | timeout por llamada | p95 x 2 |
# | corta-circuitos | 5 fallos / 30 s |
# | cache exacta | TTL 1 a 24 h, clave con modelo + version + ambito |
# | cache semantica | similitud >= 0,95 |
# | tope por agente | 10 a 15 pasos |
# | presupuesto | alerta al 80%, corte al 100% |
#
# ### Tarea entre sesiones
#
# Instrumenta **costo por tenant** en tu sistema real y trae el nombre del cliente que
# mas margen consume. Es el dato que abre la conversacion con negocio.
