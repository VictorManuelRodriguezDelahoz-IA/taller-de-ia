# %% [markdown]
# # Sesion 3 - CI/CD y observabilidad
#
# **Taller AI DevOps - ClickIT** | Laboratorio de la sesion 3
#
# Objetivo: **un pipeline que bloquea automaticamente una regresion de calidad**,
# y trazas suficientes para depurar cuando algo se rompa.
#
# | # | Idea de la sesion | Lo que haras aqui |
# |---|---|---|
# | 1 | Esquema de trazas | Emitir un flujo de 2 pasos y leer el arbol |
# | 2 | El gate que bloquea | Leer `gate.yaml` y evaluarlo |
# | 3 | Provocar una regresion | Ver el pipeline devolver exit code 1 |
# | 4 | Canario y rollback | Cortar por senal y medir el rollback de verdad |
# | 5 | Deriva de entrada | Detectar que los datos cambiaron, no el codigo |

# %%
import sys, json, time, subprocess, random
from pathlib import Path
from collections import Counter, defaultdict

RAIZ = Path.cwd()
if not (RAIZ / "lab_utils.py").exists():
    RAIZ = RAIZ.parent
sys.path.insert(0, str(RAIZ))

import lab_utils as L
from lab_utils import chat, tabla, barra
from evaluador import correr_eval, comparar, guardar
from ci_eval import leer_gate, evaluar_gate

CASOS = L.cargar_golden()
print("Gate configurado:", json.dumps(leer_gate(), indent=2))

# %% [markdown]
# ---
# ## 1. El esquema de trazas
#
# Los campos de la slide no son decorativos: sin `prompt_id`, `tokens_cached`,
# `cost_usd` y `user_or_tenant` no puedes depurar, ni repartir costo, ni detectar
# degradacion silenciosa.
#
# Montamos un flujo de **dos pasos** (recuperar contexto -> clasificar) bajo un mismo
# `trace_id`, que es como se ve un agente de verdad.

# %%
L.limpiar_trazas()
p2 = L.cargar_prompt("clasificar_incidente.v2.yaml")

def flujo_dos_pasos(ticket, tenant="acme"):
    trace = "trace-" + str(abs(hash(ticket)) % 100000)

    # paso 1: decidir si hace falta contexto extra (modelo pequeno, barato)
    r1 = chat("Responde SOLO con JSON {\"necesita_runbook\": true|false}. "
              "Categoria del ticket y si hace falta consultar el runbook.\n\nTicket: " + ticket,
              modelo="sim-small", formato_json=True, prompt_id="triage:v1",
              trace_id=trace, tenant=tenant)

    # paso 2: clasificar (hijo del paso 1)
    r2 = chat(L.render(p2["plantilla"], ticket=ticket), modelo="sim-small",
              formato_json=True, prompt_id="clasificar:v2",
              trace_id=trace, parent_span_id=r1.span_id, tenant=tenant)
    return r2

for c in CASOS[:3]:
    flujo_dos_pasos(c["entrada"], tenant=random.choice(["acme", "globex"]))

tabla([{k: t[k] for k in ("trace_id", "span_id", "parent_span_id", "prompt_id",
                          "tokens_in", "tokens_out", "cost_usd" if "cost_usd" in t else "costo_usd",
                          "latencia_ms", "estado", "tenant")}
       for t in L.TRAZAS])

# %% [markdown]
# ### EJERCICIO 1
#
# Escribe `arbol(trace_id)` que imprima la jerarquia de un request:
#
# ```
# trace-1234
#   triage:v1            120 ms   0.000012 USD
#     clasificar:v2      380 ms   0.000090 USD
# ```
#
# Y luego `campos_faltantes(traza)`, que compruebe contra la lista de la slide y
# avise de que campo no estas emitiendo. En tu sistema real, **casi seguro falta
# `tokens_cached` o `user_or_tenant`**.

# %%
CAMPOS_OBLIGATORIOS = ["trace_id", "span_id", "parent_span_id", "timestamp", "prompt_id",
                       "modelo", "tokens_in", "tokens_cached", "tokens_out", "costo_usd",
                       "latencia_ms", "ttft_ms", "intentos", "estado", "tenant"]

def arbol(trace_id):
    # TODO: filtra L.TRAZAS por trace_id y ordena por timestamp; indenta los hijos
    ...

def campos_faltantes(traza):
    # TODO: devuelve los campos de CAMPOS_OBLIGATORIOS que no estan en la traza
    ...

print("faltan:", campos_faltantes(L.TRAZAS[0]))

# %% [markdown]
# ---
# ## 2. El gate: bloquear, no comentar
#
# El archivo `gate.yaml` es el contrato. Lo que no este escrito ahi, no existe:
# el umbral no vive en la cabeza del lider tecnico.

# %%
print(open(RAIZ / "gate.yaml", encoding="utf-8").read())

cfg = leer_gate()
baseline_path = RAIZ / "resultados" / "baseline.json"
baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else None

resultado_ok = correr_eval(cfg["prompt"], runs_por_caso=cfg["runs_per_case"], etiqueta="candidato v2")
pasa, motivos = evaluar_gate(resultado_ok, cfg, baseline)
print("score %.4f | esquema %.4f | costo/caso %.6f | p95 %d ms"
      % (resultado_ok["score_global"], resultado_ok["validez_esquema"],
         resultado_ok["costo_por_caso_usd"], resultado_ok["latencia_p95_ms"]))
print("GATE:", "PASA" if pasa else "BLOQUEA", motivos)

# %% [markdown]
# ### Por que `runs_per_case`
#
# Con una sola pasada mides **ruido**, no calidad. Compruebalo: corre el mismo prompt
# con 1 pasada varias veces y mira cuanto se mueve el puntaje.

# %%
sueltos = [correr_eval(cfg["prompt"], runs_por_caso=1)["score_global"] for _ in range(4)]
promediados = [correr_eval(cfg["prompt"], runs_por_caso=3)["score_global"] for _ in range(2)]
print("con 1 pasada :", sueltos, " -> rango %.3f" % (max(sueltos) - min(sueltos)))
print("con 3 pasadas:", promediados, " -> rango %.3f" % (max(promediados) - min(promediados)))
print("\nSi tu umbral esta a menos de un rango de distancia del puntaje, tu gate")
print("va a bloquear cambios buenos y dejar pasar malos. Sube runs_per_case.")

# %% [markdown]
# ---
# ## 3. Provocar la regresion (el paso que valida el pipeline)
#
# `ci_eval.py` es el comando que correria en CI. Lo llamamos como lo llamaria el
# pipeline y miramos **el codigo de salida**: 0 pasa, 1 bloquea la fusion.

# %%
def correr_ci(prompt=None):
    cmd = [sys.executable, "ci_eval.py"] + (["--prompt", prompt] if prompt else [])
    r = subprocess.run(cmd, cwd=str(RAIZ), capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout

codigo, salida = correr_ci("clasificar_incidente.v3_roto.yaml")
print(salida[-1200:])
print("\n>>> exit code =", codigo, "->", "BLOQUEA LA FUSION" if codigo else "deja pasar")

# %% [markdown]
# ### EJERCICIO 2
#
# 1. Baja `score_global` en `gate.yaml` a `0.30` y vuelve a correr la celda anterior.
#    Comprueba que el prompt roto **pasa**. Un umbral generoso es un gate decorativo.
# 2. Devuelvelo a `0.90` y anade un umbral nuevo: `exactitud_categoria: 0.90`.
#    Tendras que tocar `evaluar_gate` en `ci_eval.py`.
# 3. Escribe el mensaje que el pipeline dejaria en el PR: puntaje, diff por grupo y
#    **enlace a los casos que empeoraron**. Un gate que no explica que rompio se
#    acaba desactivando.

# %%
def informe_pr(anterior, nuevo, casos=CASOS):
    """Lo que se publica como comentario del pipeline."""
    lineas = ["### Eval gate", "",
              "| metrica | antes | ahora | delta |", "|---|---|---|---|"]
    for m in ("score_global", "exactitud_categoria", "validez_esquema"):
        lineas.append("| %s | %.3f | %.3f | %+.3f |" % (m, anterior[m], nuevo[m], nuevo[m] - anterior[m]))
    # TODO: anade una seccion con los grupos que caen mas de 0.05 y los 3 casos
    #       concretos con peor puntaje (usa nuevo["pares"] junto con `casos`)
    return "\n".join(lineas)

print(informe_pr(baseline or resultado_ok, resultado_ok))

# %% [markdown]
# ---
# ## 4. Canario y rollback
#
# El canario manda un porcentaje del trafico real a la version nueva y la compara
# con la anterior usando **las mismas metricas**. Tres senales de corte: puntaje
# online, tasa de error y costo por tarea.

# %%
CONFIG = {"version_activa": "clasificar_incidente.v2.yaml",
          "version_canario": "clasificar_incidente.v3_roto.yaml",
          "porcentaje_canario": 5}

def atender(ticket, version):
    p = L.cargar_prompt(version)
    r = chat(L.render(p["plantilla"], ticket=ticket), modelo=p["modelo"],
             temperature=p["temperature"], formato_json=p["formato_json"],
             prompt_id="%s:%s" % (p["id"], p["version"]))
    try:
        return r.json(), r.costo_usd, True
    except Exception:
        return {}, r.costo_usd, False

def puntuar(salida, esperado):
    return sum(salida.get(c) == esperado[c] for c in
               ("categoria", "severidad", "servicio", "requiere_humano")) / 4

def desplegar_canario(config, trafico, ventana=40, umbral_caida=0.10):
    """Devuelve el momento del corte (o None si el canario sobrevive la ventana)."""
    metricas = {"activa": [], "canario": []}
    errores = {"activa": 0, "canario": 0}
    for i, caso in enumerate(trafico, 1):
        rama = "canario" if (i % (100 // config["porcentaje_canario"]) == 0) else "activa"
        version = config["version_canario"] if rama == "canario" else config["version_activa"]
        salida, costo, ok = atender(caso["entrada"], version)
        metricas[rama].append(puntuar(salida, caso["esperado"]))
        errores[rama] += 0 if ok else 1
        if len(metricas["canario"]) >= 5:
            m_act = sum(metricas["activa"]) / max(1, len(metricas["activa"]))
            m_can = sum(metricas["canario"]) / len(metricas["canario"])
            if m_act - m_can > umbral_caida:
                return {"corte_en_request": i, "score_activa": round(m_act, 3),
                        "score_canario": round(m_can, 3),
                        "errores_canario": errores["canario"]}
    return None

random.seed(7)
trafico = [random.choice(CASOS) for _ in range(200)]
corte = desplegar_canario(CONFIG, trafico)
print("Resultado del canario:", corte or "sobrevivio la ventana (no deberia, la v3 esta rota)")

# %% [markdown]
# ### Rollback: se ensaya, no se supone
#
# *"Volver a la version anterior debe ser un cambio de configuracion, no un despliegue
# nuevo."* Vamos a medir cuanto tarda de verdad.

# %%
t0 = time.time()
CONFIG["version_canario"] = None
CONFIG["version_activa"] = "clasificar_incidente.v1.yaml"     # <- el rollback es esta linea
prueba, _, ok = atender(CASOS[0]["entrada"], CONFIG["version_activa"])
t_rollback = time.time() - t0
print("rollback aplicado y verificado en %.3f s | version activa: %s"
      % (t_rollback, CONFIG["version_activa"]))
print("salida de verificacion:", prueba)
print("\nSi en tu sistema el rollback exige un despliegue completo, ya sabes cual es")
print("la primera tarea de infraestructura del proyecto.")

# %% [markdown]
# ### EJERCICIO 3
#
# 1. Anade a `desplegar_canario` la **tercera senal**: costo por tarea del canario
#    mas de un 30% por encima de la rama activa -> corte.
# 2. Haz que el canario se promocione solo si sobrevive **toda** la ventana con las
#    tres senales en verde, y que devuelva un informe con los tres numeros.
# 3. Fija la version exacta del modelo en `CONFIG` (`"modelo": "sim-small"`). Lo que
#    casi nadie hace: si apuntas a un alias que el proveedor actualiza, tu sistema
#    cambia sin que tu cambies nada.

# %% [markdown]
# ---
# ## 5. Deriva: cuando cambian los datos, no el codigo
#
# El sistema no se cae: responde peor. Vigila la **distribucion** de lo que llega
# (longitud y categoria), no solo los errores.

# %%
def perfil(casos):
    largos = [len(c["entrada"]) for c in casos]
    largos.sort()
    return {"n": len(casos),
            "long_mediana": largos[len(largos) // 2],
            "long_p95": largos[int(len(largos) * 0.95) - 1],
            "reparto": {k: round(v / len(casos), 3)
                        for k, v in Counter(c["esperado"]["categoria"] for c in casos).items()}}

ayer = CASOS
# hoy llegan tickets mas largos y con mucha mas seguridad de lo habitual
hoy = ([c for c in CASOS if c["esperado"]["categoria"] == "seguridad"] * 3 +
       [dict(c, entrada=c["entrada"] + " " + L.documento("correo_proveedor.md")[:400])
        for c in CASOS[:10]])

print("ayer:", json.dumps(perfil(ayer), ensure_ascii=False))
print("hoy :", json.dumps(perfil(hoy), ensure_ascii=False))

def deriva(a, b, umbral=0.15):
    """Indice simple de deriva de categoria: suma de diferencias absolutas / 2."""
    pa, pb = perfil(a)["reparto"], perfil(b)["reparto"]
    clases = set(pa) | set(pb)
    indice = sum(abs(pa.get(c, 0) - pb.get(c, 0)) for c in clases) / 2
    largo = perfil(b)["long_p95"] / max(1, perfil(a)["long_p95"])
    avisos = []
    if indice > umbral:
        avisos.append("deriva de categoria: %.2f (umbral %.2f)" % (indice, umbral))
    if largo > 1.5 or largo < 0.66:
        avisos.append("deriva de longitud: el p95 es %.1fx el de referencia" % largo)
    return avisos or ["sin deriva relevante"]

for a in deriva(ayer, hoy):
    print(" -", a)

# %% [markdown]
# ### EJERCICIO 4
#
# 1. Corre el eval **solo sobre el trafico de hoy** y compara el puntaje con el del
#    set dorado. Si baja, tu set dorado ya no representa la realidad: toca ampliarlo.
# 2. Escribe las cuatro alertas de la slide como funciones que devuelven True/False:
#    costo diario sobre presupuesto, caida del puntaje online, salto de reintentos y
#    p95 fuera de rango. Decide **para cada una** si despierta a alguien o solo avisa.

# %%
ALERTAS = {
    "costo_diario_sobre_presupuesto": lambda m: m["costo_dia_usd"] > m["presupuesto_dia_usd"],
    # TODO: caida_puntaje_online, salto_reintentos, p95_fuera_de_rango
}
metricas_hoy = {"costo_dia_usd": 12.4, "presupuesto_dia_usd": 10.0,
                "score_online": 0.83, "score_base": 0.95,
                "reintentos": 0.18, "reintentos_base": 0.04, "p95_ms": 2600, "p95_objetivo": 2000}
for nombre, f in ALERTAS.items():
    print("%-34s %s" % (nombre, "DISPARA" if f(metricas_hoy) else "ok"))

# %% [markdown]
# ---
# ## Cierre
#
# Te llevas: trazas con esquema, un `gate.yaml` versionado, un comando de CI que
# devuelve exit code 1, un canario con senal de corte, un rollback cronometrado y un
# detector de deriva.
#
# En la carpeta tienes ademas `github-workflow-ejemplo.yml`: el pipeline listo para
# copiar a `.github/workflows/` de tu repositorio real.
#
# ### Tarea entre sesiones
#
# Deja el gate **activo** en el repositorio real de tu equipo, aunque el umbral inicial
# sea generoso. Un gate flojo que corre siempre vale mas que un gate perfecto que nadie
# ha conectado.
