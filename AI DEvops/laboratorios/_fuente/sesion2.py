# %% [markdown]
# # Sesion 2 - Prompts y evaluacion
#
# **Taller AI DevOps - ClickIT** | Laboratorio de la sesion 2
#
# Objetivo de la sesion: **salir con un comando que corre tu set de casos y devuelve
# un puntaje**. Aqui lo construyes pieza a pieza.
#
# | # | Idea de la sesion | Lo que haras aqui |
# |---|---|---|
# | 1 | El prompt es un artefacto | Cargar prompts versionados y renderizarlos |
# | 2 | El set dorado | Auditar su composicion (60/30/10) y su diversidad |
# | 3 | Metricas segun el tipo de salida | Implementar 4 metricas distintas |
# | 4 | El puntaje reproducible | Un runner que guarda puntaje + version + commit |
# | 5 | Romper el prompt a proposito | Comprobar que la metrica lo detecta |
# | 6 | LLM-as-judge | Medir sus tres sesgos y corregirlos |

# %%
import sys, json, subprocess, statistics, hashlib
from pathlib import Path
from collections import Counter, defaultdict

RAIZ = Path.cwd()
if not (RAIZ / "lab_utils.py").exists():
    RAIZ = RAIZ.parent
sys.path.insert(0, str(RAIZ))

import lab_utils as L
from lab_utils import chat, tabla, barra

CASOS = L.cargar_golden()
CAMPOS = ("categoria", "severidad", "servicio", "requiere_humano")
print("Casos cargados:", len(CASOS))

# %% [markdown]
# ---
# ## 1. El prompt es un artefacto de software
#
# Versionado, separado del codigo, parametrizado y **trazable**: cada respuesta guarda
# con que version se genero. Mira `prompts/` en la carpeta del laboratorio.

# %%
for archivo in sorted(pth.name for pth in L.PROMPTS.glob("*.yaml")):
    p = L.cargar_prompt(archivo)
    print("%-34s v=%-8s modelo=%-10s temp=%-4s json=%s"
          % (archivo, p["version"], p["modelo"], p["temperature"], p["formato_json"]))
    print("   nota:", p["notas"])

V1 = L.cargar_prompt("clasificar_incidente.v1.yaml")
print("\nRenderizado (los primeros 200 caracteres):")
print(L.render(V1["plantilla"], ticket=CASOS[0]["entrada"])[:200], "...")

# %% [markdown]
# > **Por que se conserva la version anterior:** porque el rollback de un prompt debe
# > ser tan rapido como el de un despliegue, y porque necesitas comparar puntajes.
#
# ---
# ## 2. Auditoria del set dorado
#
# Composicion objetivo de la slide: **60% tipicos, 30% dificiles, 10% de rechazo**.
# La diversidad manda sobre el volumen.

# %%
dif = Counter(c["dificultad"] for c in CASOS)
cat = Counter(c["esperado"]["categoria"] for c in CASOS)
tabla([{"dificultad": k, "casos": v, "% del set": "%.0f%%" % (100 * v / len(CASOS)),
        "objetivo": {"tipico": "60%", "dificil": "30%", "rechazo": "10%"}[k]}
       for k, v in dif.items()])
print()
tabla([{"categoria": k, "casos": v, "reparto": barra(v / max(cat.values()), 20)}
       for k, v in cat.most_common()])

# %% [markdown]
# ### EJERCICIO 1
#
# Escribe `auditar(casos)` que avise de los tres problemas tipicos de un set dorado:
#
# 1. alguna categoria con **menos de 3 casos** (no podras medir esa clase)
# 2. proporcion de dificiles **por debajo del 20%** (el set es demasiado facil)
# 3. casos **duplicados** (inflan el puntaje sin aportar informacion)

# %%
def auditar(casos):
    avisos = []
    # TODO: 1) categorias con menos de 3 casos
    # TODO: 2) % de dificiles < 20
    # TODO: 3) entradas duplicadas
    return avisos

print(auditar(CASOS) or "sin avisos (revisa si tu auditoria esta realmente comprobando algo)")

# %% [markdown]
# ---
# ## 3. Metricas: la mas barata que detecte el fallo
#
# Nuestra salida es JSON con campos, asi que la slide manda:
# **validacion de esquema + coincidencia campo a campo**, y ademas exactitud por clase.
# El juez LLM es el ultimo recurso, no el primero.

# %%
def valido(d):
    return (isinstance(d, dict)
            and d.get("categoria") in L.CATEGORIAS
            and d.get("severidad") in L.SEVERIDADES
            and isinstance(d.get("servicio"), str)
            and isinstance(d.get("requiere_humano"), bool))

def coincidencia_campos(obtenido, esperado):
    """Campos correctos / campos esperados. Es la metrica principal del laboratorio."""
    if not isinstance(obtenido, dict):
        return 0.0
    return sum(obtenido.get(c) == esperado[c] for c in CAMPOS) / len(CAMPOS)

def matriz_confusion(pares):
    """pares = [(real, predicho), ...]"""
    clases = sorted(set([r for r, _ in pares]) | set([p for _, p in pares if p]))
    m = {r: {c: 0 for c in clases} for r in clases}
    for real, pred in pares:
        if pred in m[real]:
            m[real][pred] += 1
    return clases, m

def precision_recall(pares, clase):
    tp = sum(1 for r, p in pares if r == clase and p == clase)
    fp = sum(1 for r, p in pares if r != clase and p == clase)
    fn = sum(1 for r, p in pares if r == clase and p != clase)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return round(prec, 3), round(rec, 3)

print("Metricas listas. Ninguna llama a un LLM: son deterministas y cuestan cero.")

# %% [markdown]
# ---
# ## 4. El runner: de "parece que va bien" a un numero reproducible
#
# Regla de oro de la slide: el puntaje se guarda junto al **hash del commit**, la
# **version del prompt** y el **id del modelo**. Sin eso no es comparable.

# %%
def hash_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=str(RAIZ), stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "sin-git"

def correr_eval(archivo_prompt, casos=CASOS, runs_por_caso=3, modelo=None, etiqueta=""):
    p = L.cargar_prompt(archivo_prompt)
    modelo = modelo or p["modelo"]
    prompt_id = "%s:%s" % (p["id"], p["version"])
    L.limpiar_trazas()

    pares, campos, validos, detalle = [], [], 0, defaultdict(list)
    for c in casos:
        for _ in range(runs_por_caso):
            r = chat(L.render(p["plantilla"], ticket=c["entrada"]), modelo=modelo,
                     temperature=p["temperature"], formato_json=p["formato_json"],
                     max_tokens=p["max_tokens"], prompt_id=prompt_id)
            try:
                d = r.json()
            except Exception:
                d = None
            validos += 1 if valido(d) else 0
            pares.append((c["esperado"]["categoria"], (d or {}).get("categoria")))
            punt = coincidencia_campos(d, c["esperado"])
            campos.append(punt)
            detalle[c["dificultad"]].append(punt)
            detalle["cat:" + c["esperado"]["categoria"]].append(punt)

    tr = L.resumen_trazas()
    n = len(campos)
    return {
        "etiqueta": etiqueta or archivo_prompt,
        "prompt_id": prompt_id,
        "modelo": modelo,
        "commit": hash_commit(),
        "casos": len(casos), "runs_por_caso": runs_por_caso,
        "score_global": round(sum(campos) / n, 4),
        "exactitud_categoria": round(sum(1 for r, pr in pares if r == pr) / n, 4),
        "validez_esquema": round(validos / n, 4),
        "por_grupo": {k: round(sum(v) / len(v), 4) for k, v in sorted(detalle.items())},
        "costo_usd": tr["costo_total_usd"],
        "costo_por_caso_usd": round(tr["costo_total_usd"] / n, 6),
        "latencia_p95_ms": tr["latencia_p95_ms"],
        "pares": pares,
    }

base = correr_eval("clasificar_incidente.v1.yaml", etiqueta="v1 (base)")
print(json.dumps({k: v for k, v in base.items() if k != "pares"}, indent=2, ensure_ascii=False))

# %% [markdown]
# ### La matriz de confusion: donde se pierde el puntaje
#
# Un promedio estable puede esconder que una clase entera se rompio. Por eso se
# reporta **siempre** el global Y el desglose.

# %%
clases, m = matriz_confusion(base["pares"])
print("filas = real, columnas = predicho")
tabla([dict({"real": r}, **{c: m[r][c] for c in clases}) for r in clases])
print()
tabla([{"clase": c, "precision": precision_recall(base["pares"], c)[0],
        "exhaustividad": precision_recall(base["pares"], c)[1]} for c in clases])

# %% [markdown]
# ---
# ## 5. Comparar versiones de prompt
#
# Esto es lo que en la Sesion 3 se convierte en el **gate**: no basta con que suba el
# global, ninguna categoria puede caer mas de X puntos.

# %%
mejor = correr_eval("clasificar_incidente.v2.yaml", etiqueta="v2 (con ejemplos y rubrica)")
roto  = correr_eval("clasificar_incidente.v3_roto.yaml", etiqueta="v3 (empeorada a proposito)")

tabla([{"version": r["etiqueta"], "score": r["score_global"],
        "exact_categoria": r["exactitud_categoria"], "esquema": r["validez_esquema"],
        "costo/caso": r["costo_por_caso_usd"], "p95_ms": r["latencia_p95_ms"]}
       for r in (base, mejor, roto)])

print("\nDiff por grupo (v2 menos v1): un solo numero global no basta")
filas = []
for g in sorted(base["por_grupo"]):
    d = round(mejor["por_grupo"][g] - base["por_grupo"][g], 3)
    filas.append({"grupo": g, "v1": base["por_grupo"][g], "v2": mejor["por_grupo"][g],
                  "delta": ("+" if d >= 0 else "") + str(d),
                  "": "SUBE" if d > 0.01 else ("BAJA" if d < -0.01 else "igual")})
tabla(filas)

# %% [markdown]
# ### El paso que valida todo lo anterior
#
# > *"Una metrica que no baja cuando empeoras el prompt es una metrica decorativa.
# > Muchos equipos operan meses con evaluaciones que no detectan nada."*

# %%
caida = base["score_global"] - roto["score_global"]
print("v1: %.3f | v3 rota: %.3f | caida: %.3f" % (base["score_global"], roto["score_global"], caida))
print("Veredicto:", "la metrica SIRVE" if caida > 0.10 else "la metrica es DECORATIVA, cambiala")

# %% [markdown]
# ### EJERCICIO 2
#
# 1. Guarda los tres resultados en `resultados/` con el nombre
#    `eval_<prompt_id>_<commit>.json`. Sin eso no hay historico ni comparacion.
# 2. Escribe `comparar(anterior, nuevo, caida_maxima=0.05)` que devuelva
#    `("BLOQUEAR", motivos)` si **alguna** clase cae mas de `caida_maxima`,
#    aunque el global suba. Es literalmente el gate de la Sesion 3.

# %%
DEST = RAIZ / "resultados"
DEST.mkdir(exist_ok=True)

def guardar(resultado):
    # TODO: escribe el json (sin la clave "pares") en DEST y devuelve la ruta
    ...

def comparar(anterior, nuevo, caida_maxima=0.05):
    motivos = []
    # TODO: recorre nuevo["por_grupo"] y compara con anterior["por_grupo"]
    return ("BLOQUEAR" if motivos else "PASA"), motivos

print(comparar(base, roto))
# Esperado cuando lo resuelvas: ('BLOQUEAR', [...varios grupos...])

# %% [markdown]
# ---
# ## 6. LLM-as-judge: util, pero no inocente
#
# Cuando la salida es texto libre no hay coincidencia exacta posible y toca un juez.
# Antes de usarlo hay que **validarlo**: se compara contra juicios humanos y si no
# coincide en al menos el **80%**, el juez no sirve todavia.
#
# Montamos 20 comparaciones A/B. En todas, la respuesta correcta es la **breve y
# exacta**; la incorrecta es **larga, florida y equivocada**. Un humano acierta el 100%.

# %%
def par_de_respuestas(caso):
    e = caso["esperado"]
    buena = json.dumps(e, ensure_ascii=False)
    mala = json.dumps(dict(e, categoria="aplicacion" if e["categoria"] != "aplicacion" else "datos",
                           severidad="media"), ensure_ascii=False)
    mala = ("Tras un analisis detallado del ticket y considerando el impacto potencial "
            "sobre los distintos equipos implicados, la valoracion mas prudente y "
            "completa que puedo ofrecer es la siguiente: " + mala +
            " Espero que esta explicacion resulte de utilidad para el equipo.")
    return buena, mala

PARES = [par_de_respuestas(c) for c in CASOS[:20]]

RUBRICA_INGENUA = """Eres un juez de calidad. Puntua cual de las dos respuestas clasifica
mejor el ticket. Responde SOLO con JSON: {"ganador": "A" o "B"}.

Ticket: {{ticket}}

Respuesta A: {{a}}
Respuesta B: {{b}}"""

def juzgar(rubrica, ticket, a, b, referencia=None):
    pr = L.render(rubrica, ticket=ticket, a=a, b=b,
                  **({"referencia": referencia} if "{{referencia}}" in rubrica else {}))
    try:
        return chat(pr, modelo="sim-large", temperature=0, prompt_id="juez").json().get("ganador")
    except Exception:
        return None

# El humano siempre prefiere la breve y correcta.
aciertos = 0
for c, (buena, mala) in zip(CASOS[:20], PARES):
    g = juzgar(RUBRICA_INGENUA, c["entrada"], buena, mala)   # la buena va SIEMPRE en A
    aciertos += (g == "A")
print("Juez ingenuo, la buena siempre en A: acuerdo con el humano = %.0f%%" % (100 * aciertos / 20))

aciertos = 0
for c, (buena, mala) in zip(CASOS[:20], PARES):
    g = juzgar(RUBRICA_INGENUA, c["entrada"], mala, buena)   # ahora la buena va en B
    aciertos += (g == "B")
print("Juez ingenuo, la buena siempre en B: acuerdo con el humano = %.0f%%" % (100 * aciertos / 20))

# %% [markdown]
# Si los dos numeros de arriba son muy distintos, acabas de **medir el sesgo de
# posicion y el de verbosidad** en tu propio juez. Un juez asi no puede entrar en un gate.
#
# ### EJERCICIO 3: arregla el juez
#
# La slide da la receta. Aplicala en `RUBRICA_BUENA`:
#
# 1. **criterio unico** por llamada
# 2. **penalizar el relleno** de forma explicita (`penaliza el relleno`)
# 3. decirle que **el orden es aleatorio** para neutralizar la posicion
# 4. darle la **respuesta de referencia** (`Respuesta de referencia: ...`)
#
# Objetivo: pasar del ~50% al **>= 80%** de acuerdo, en los dos ordenes.

# %%
RUBRICA_BUENA = """Eres un juez de calidad. Criterio unico: que respuesta coincide mejor
con la respuesta de referencia. El orden es aleatorio, ignora la posicion.
Penaliza el relleno: la extension no suma puntos.
Responde SOLO con JSON: {"ganador": "A" o "B"}.

Ticket: {{ticket}}
Respuesta de referencia: {{referencia}}

Respuesta A: {{a}}
Respuesta B: {{b}}"""

def acuerdo(rubrica, invertir=False):
    ok = 0
    for c, (buena, mala) in zip(CASOS[:20], PARES):
        ref = json.dumps(c["esperado"], ensure_ascii=False)
        a, b = (mala, buena) if invertir else (buena, mala)
        esperado = "B" if invertir else "A"
        ok += juzgar(rubrica, c["entrada"], a, b, referencia=ref) == esperado
    return ok / 20

print("Juez con rubrica corregida:")
print("  buena en A: %.0f%%" % (100 * acuerdo(RUBRICA_BUENA)))
print("  buena en B: %.0f%%" % (100 * acuerdo(RUBRICA_BUENA, invertir=True)))
print("\nRegla: si no llega al 80% en AMBOS ordenes, el juez no entra en el gate.")

# %% [markdown]
# ### EJERCICIO 4 (opcional, 10 min)
#
# Implementa el control canonico: **correr cada par en los dos ordenes y promediar**.
# Si los dos ordenes se contradicen, el caso se marca `empate` y se manda a revision
# humana en vez de contarlo como acierto.

# %%
def juicio_robusto(ticket, buena, mala, referencia):
    # TODO: juzga (buena, mala) y (mala, buena). Si coinciden devuelve el ganador real;
    #       si se contradicen devuelve "empate".
    ...

# %% [markdown]
# ---
# ## Cierre
#
# Tienes: un prompt versionado, un set dorado auditado, cuatro metricas deterministas,
# un runner reproducible (puntaje + version + commit + costo + p95) y un juez validado.
#
# ### Tarea entre sesiones
#
# 1. Sustituye `datos/golden_incidentes.jsonl` por **tu** set (mismo formato).
# 2. Corre `correr_eval` con tu prompt actual y **anota el puntaje base**. Ese numero
#    es el que la Sesion 3 va a defender con un gate.
# 3. Empeora tu prompt a proposito y comprueba que el puntaje baja. Si no baja, tu
#    metrica todavia no sirve.
