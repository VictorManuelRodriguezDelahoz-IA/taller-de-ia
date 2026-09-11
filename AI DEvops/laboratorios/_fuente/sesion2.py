# %% [markdown]
# # Sesión 2 · Evaluación de LLMs: de "parece que funciona" a un número reproducible
#
# **Taller AI DevOps · ClickIT** · Laboratorio de la sesión 2 · 35-40 minutos
#
# ## El problema
#
# En software tradicional una prueba es un `assert`: misma entrada, misma salida; pasa o
# falla. Con un LLM eso no funciona, por dos motivos:
#
# - La salida es **estocástica**: la misma entrada puede dar respuestas distintas.
# - Los fallos son **silenciosos**: el modelo no lanza una excepción, responde algo plausible
#   pero incorrecto.
#
# Por eso un sistema con LLM no se prueba con asserts: se **evalúa**. Toda evaluación tiene
# tres piezas:
#
# 1. **Un conjunto de casos** con su respuesta correcta (*golden set*).
# 2. **Una métrica** que compara la salida del sistema con esa respuesta.
# 3. **Un umbral** que decide si el resultado es aceptable.
#
# Imagen mental: **un examen con su hoja de respuestas**, que se corrige igual cada vez.
#
# ## Conceptos que vas a usar
#
# | Concepto | Definición | En este laboratorio |
# |---|---|---|
# | **Ground truth** | La respuesta correcta de un caso, escrita por una persona | El campo `esperado` de cada ticket |
# | **Predicción** | Lo que devuelve el modelo para un caso | Cada respuesta del clasificador |
# | **Golden set** (set dorado) | Conjunto de casos reales, cada uno con su ground truth | 40 tickets de incidentes |
# | **Eval** | Ejecutar el sistema sobre el golden set y medirlo con una métrica | `correr_eval()` |
# | **Métrica determinista** | Se calcula con código, sin llamar a otro modelo: gratis y repetible | Validez de esquema, acierto por campo |
# | **Regresión** | Un cambio que empeora la calidad en algún grupo de casos | Pasos 5 y 6 |
# | **LLM-as-judge** | Usar un modelo para puntuar salidas que no admiten comparación exacta | Paso 7 |
#
# ## Lo que vas a hacer
#
# | Paso | Qué haces | Concepto técnico |
# |---|---|---|
# | 1 | Evaluar un solo caso | Parseo, validación de esquema y acierto por campo |
# | 2 | Analizar el golden set | Estratificación, cobertura y resolución de la métrica |
# | 3 | Correr el eval completo | Varianza, reproducibilidad y agregación |
# | 4 | Analizar los errores | Matriz de confusión, precision y recall |
# | 5 | Comparar dos versiones del prompt | Regresión por grupo, señal frente a ruido |
# | 6 | Romper el prompt a propósito | Validar que la métrica detecta defectos |
# | 7 | Usar un LLM como juez | Sesgos de posición y de longitud, y cómo controlarlos |
#
# > Ejecuta con **Run All** o celda a celda con **Shift + Enter**. No necesitas API key: el
# > modelo es un simulador que reproduce el comportamiento de un LLM real. Las celdas marcadas
# > **EJERCICIO** tienen un `TODO` y te dicen si ya está resuelto.

# %%
# Preparación: ejecuta esta celda primero
import sys, json
from pathlib import Path
from collections import Counter

RAIZ = Path.cwd()
if not (RAIZ / "lab_utils.py").exists():
    RAIZ = RAIZ.parent
sys.path.insert(0, str(RAIZ))

import lab_utils as L
from lab_utils import chat, barra
from evaluador import correr_eval, boletin, comparar_versiones, donde_se_equivoca

CASOS = L.cargar_golden()
CAMPOS = ["categoria", "severidad", "servicio", "requiere_humano"]
print("Golden set cargado:", len(CASOS), "casos.")

# %% [markdown]
# ---
# ## Paso 1 · Anatomía de la evaluación de un caso
#
# El sistema recibe un ticket y devuelve un **JSON con cuatro campos**:
#
# | Campo | Tipo | Valores permitidos |
# |---|---|---|
# | `categoria` | enum (lista cerrada de valores) | infraestructura, aplicacion, seguridad, datos, spam |
# | `severidad` | enum (lista cerrada de valores) | critica, alta, media, baja |
# | `servicio` | string | nombre del servicio, o "desconocido" |
# | `requiere_humano` | bool | True / False |
#
# El modelo también devuelve un campo `confianza`. No forma parte del ground truth, así que **no se
# puntúa**: la validación comprueba que estén los campos obligatorios, y los campos extra no la invalidan.
#
# Evaluar un caso tiene **tres etapas**, y cada una puede fallar por separado:
#
# 1. **Parseo:** ¿la respuesta es JSON? Si el modelo añade texto alrededor, falla aquí.
# 2. **Validación de esquema:** ¿están todos los campos, con el tipo correcto y valores permitidos?
# 3. **Comparación con el ground truth:** ¿cuántos campos coinciden?
#
# La métrica principal es el **acierto por campo** (*field-level accuracy*):
#
# $$\text{acierto por campo} = \frac{\text{campos que coinciden con el ground truth}}{\text{campos totales}}$$
#
# ¿Por qué no comparar el JSON entero (*exact match*)? Porque es todo o nada: una respuesta con
# 3 de 4 campos bien valdría lo mismo que una con 0 de 4, y perderías la información de **qué**
# campo falla.
#
# Así se implementan las tres etapas:

# %%
PROMPT_V1 = L.cargar_prompt("clasificar_incidente.v1.yaml")

def llamar_modelo(ticket, prompt=PROMPT_V1):
    """Devuelve el texto crudo que responde el modelo."""
    texto = L.render(prompt["plantilla"], ticket=ticket)
    r = chat(texto, modelo=prompt["modelo"], temperature=prompt["temperature"],
             formato_json=prompt["formato_json"])
    return r.texto

def parsear(texto):
    """Etapa 1: texto -> dict. None si no hay JSON legible."""
    try:
        return json.loads(L.extraer_json(texto))
    except Exception:
        return None

def es_valido(d):
    """Etapa 2: validación de esquema (campos, tipos y valores permitidos)."""
    return (isinstance(d, dict)
            and d.get("categoria") in L.CATEGORIAS
            and d.get("severidad") in L.SEVERIDADES
            and isinstance(d.get("servicio"), str)
            and isinstance(d.get("requiere_humano"), bool))

def acierto_por_campo(prediccion, ground_truth):
    """Etapa 3: fracción de campos que coinciden con el ground truth."""
    if not isinstance(prediccion, dict):
        return 0.0
    return sum(prediccion.get(c) == ground_truth[c] for c in CAMPOS) / len(CAMPOS)

print("Listas las funciones: llamar_modelo, parsear (etapa 1), es_valido (etapa 2), acierto_por_campo (etapa 3).")

# %% [markdown]
# Ahora aplicamos las tres etapas a dos casos del golden set: uno típico y uno difícil.

# %%
def evaluar_un_caso(caso, prompt=PROMPT_V1):
    crudo = llamar_modelo(caso["entrada"], prompt)
    pred = parsear(crudo)
    print("TICKET:", caso["entrada"])
    print("RESPUESTA CRUDA:", crudo[:140])
    print("")
    print("  1. Parseo JSON:      ", "ok" if pred is not None else "FALLA")
    print("  2. Esquema válido:   ", "ok" if es_valido(pred) else "FALLA")
    print("  3. Comparación con el ground truth:")
    print("")
    print("     %-16s %-20s %-20s" % ("campo", "ground truth", "predicción"))
    for campo in CAMPOS:
        gt = caso["esperado"][campo]
        pr = (pred or {}).get(campo, "(sin valor)")
        print("     %-16s %-20s %-20s %s" % (campo, str(gt), str(pr), "ok" if pr == gt else "FALLA"))
    nota = acierto_por_campo(pred, caso["esperado"])
    print("")
    print("  Acierto por campo: %.2f" % nota)
    return nota

facil = CASOS[0]
dificil = next(c for c in CASOS if c["id"] == "CASO-025")

evaluar_un_caso(facil)
print("")
print("-" * 76)
print("")
nota_dificil = evaluar_un_caso(dificil)

# %% [markdown]
# **Cómo leer el resultado**
#
# - Las etapas 1 y 2 miden la **forma** de la respuesta; la etapa 3 mide el **contenido**. Son
#   fallos distintos con arreglos distintos: la forma se arregla con salida estructurada y
#   validación; el contenido, con mejores instrucciones o más contexto.
# - El segundo ticket es **difícil** a propósito: mezcla señales de infraestructura (*pod,
#   memoria*) y de aplicación (*deploy, error 500*). Ahí es donde suele fallar algún campo.
#
# **Lo que te llevas:** para salidas estructuradas, la métrica más barata y precisa es comparar
# campo por campo con el ground truth. No hace falta un juez (diapositiva 25).

# %% [markdown]
# ---
# ## Paso 2 · El golden set: diseño del dataset
#
# Un eval es tan bueno como sus casos. Tres decisiones de diseño (diapositiva 24):
#
# - **Casos reales, no sintéticos.** Los inventados son más limpios que la realidad: el eval
#   daría una nota alta que no se sostiene en producción.
# - **El ground truth lo escribe quien hace hoy ese trabajo**, no quien construye el sistema.
#   Así se evita el *sesgo del constructor*.
# - **Estratificación por dificultad:** ~60% típicos, ~30% difíciles y ~10% que el sistema
#   debe rechazar. Si solo hay casos fáciles, la nota no distingue un prompt bueno de uno regular.
#
# Cada caso es una línea de un archivo `.jsonl`:

# %%
print(json.dumps(CASOS[0], indent=2, ensure_ascii=False))

# %%
por_dificultad = Counter(c["dificultad"] for c in CASOS)
objetivo = {"tipico": 60, "dificil": 30, "rechazo": 10}

print("Estratificación por dificultad:")
for dificultad in ("tipico", "dificil", "rechazo"):
    n = por_dificultad[dificultad]
    print("  %-8s %2d casos = %3.0f%%   (objetivo %d%%)  %s"
          % (dificultad, n, 100 * n / len(CASOS), objetivo[dificultad], barra(n / len(CASOS), 20)))

print("")
por_categoria = Counter(c["esperado"]["categoria"] for c in CASOS)
print("Cobertura por categoría:")
for categoria, n in por_categoria.most_common():
    print("  %-16s %2d  %s" % (categoria, n, barra(n / max(por_categoria.values()), 20)))

# %% [markdown]
# ### Resolución de la métrica
#
# Un concepto que casi nadie mira: con pocos casos, la nota de un grupo **solo puede moverse a
# saltos**. Si una categoría tiene $n$ casos y cada caso tiene 4 campos, el cambio mínimo posible
# (un campo que pasa de bien a mal en las 3 corridas) es:
#
# $$\text{resolución} = \frac{1}{n \times 4}$$
#
# Con 10 casos, un campo mal mueve la nota de la categoría 0,025. Con 2 casos, **0,125**. Cuanto
# peor es la resolución, más fácil es confundir ruido con una regresión.

# %%
print("  %-16s %6s %12s" % ("categoría", "casos", "resolución"))
for categoria, n in por_categoria.most_common():
    print("  %-16s %6d %12.3f" % (categoria, n, 1 / (n * len(CAMPOS))))

# %% [markdown]
# ### EJERCICIO 1 · Detectar categorías con cobertura insuficiente
#
# Completa la función para que devuelva las categorías con **menos de 3 casos**. En un pipeline
# real, esta comprobación se ejecuta antes del eval y avisa de que el dataset no permite medir
# esa categoría con fiabilidad.

# %%
def categorias_con_pocos_casos(casos, minimo=3):
    cuenta = Counter(c["esperado"]["categoria"] for c in casos)
    pocas = []
    # TODO: recorre `cuenta` y añade a `pocas` cada categoría con menos de `minimo` casos
    return pocas

resultado = categorias_con_pocos_casos(CASOS)
print("Categorías con menos de 3 casos:", resultado)
print("OK: su resolución es 0,125. Apúntalo, vuelve a salir en el paso 5." if resultado == ["spam"]
      else "Todavía no: debería salir ['spam'].")

# %% [markdown]
# ---
# ## Paso 3 · El eval completo: varianza, reproducibilidad y agregación
#
# Ahora aplicamos el paso 1 a los 40 casos. Hay tres decisiones técnicas detrás:
#
# **1. Varias corridas por caso (`runs_por_caso`).** El modelo es estocástico: incluso con
# `temperature = 0` la salida puede variar entre llamadas. Con una sola corrida, parte de lo que
# mides es ruido. Aquí cada caso se evalúa 3 veces: 40 × 3 = **120 predicciones**.
#
# **2. Reproducibilidad.** Una nota solo es comparable si sabes exactamente qué la produjo. Cada
# resultado guarda:
#
# - `prompt_id`: nombre y versión del prompt, por ejemplo `clasificar_incidente:v1`
# - `modelo`: el identificador exacto del modelo
# - `commit`: el hash de git del código
#
# **3. Agregación.** Se reporta la media sobre las 120 predicciones (**nota global**) y también la
# media por grupo (**por dificultad y por categoría**). La media global sola esconde problemas
# localizados: lo verás en el paso 5.
#
# Este es el bucle por dentro, en su versión mínima y sobre 5 casos:

# %%
def eval_minimo(casos, prompt, runs_por_caso=3):
    notas, validas = [], 0
    for caso in casos:
        for _ in range(runs_por_caso):
            pred = parsear(llamar_modelo(caso["entrada"], prompt))
            validas += es_valido(pred)
            notas.append(acierto_por_campo(pred, caso["esperado"]))
    n = len(notas)
    return {"predicciones": n,
            "nota_global": round(sum(notas) / n, 3),
            "validez_esquema": round(validas / n, 3)}

print(eval_minimo(CASOS[:5], PROMPT_V1))

# %% [markdown]
# 5 casos × 3 corridas = 15 predicciones. Con tan pocos casos la nota no es fiable: por eso el eval
# real usa los 40.
#
# La versión completa está en `evaluador.py` (`correr_eval`). Hace lo mismo sobre los 40 casos y
# además calcula la nota por grupo, registra el costo y la latencia de cada llamada y guarda el
# `commit`. `boletin()` solo imprime el resultado de forma legible.

# %%
v1 = correr_eval("clasificar_incidente.v1.yaml", etiqueta="prompt v1")
boletin(v1)

# %% [markdown]
# **Cómo leer el boletín**
#
# | Métrica | Definición | Para qué sirve |
# |---|---|---|
# | **Nota global** | Media del acierto por campo sobre las 120 predicciones | La métrica principal |
# | **Acierta la categoría** | *Accuracy* del campo `categoria`: predicciones con la categoría correcta / total | El campo con más impacto en la operación |
# | **JSON válido** | Tasa de validez de esquema | Si baja, la integración se rompe aunque el contenido sea correcto |
# | **Costo por predicción** | Tokens de entrada × precio + tokens de salida × precio | El costo unitario de esa calidad |
# | **Tiempo (p95)** | Percentil 95 de la latencia: el 95% de las llamadas tarda menos | El promedio esconde la cola lenta, que es la que sufre el usuario |
# | **Nota por grupo** | Media restringida a un subconjunto de casos | Localizar dónde se pierde la nota |
# | **commit** | Hash de git del código evaluado | Saber qué cambió entre dos notas |

# %% [markdown]
# ---
# ## Paso 4 · Análisis de errores: matriz de confusión, precision y recall
#
# La nota dice **cuánto** falla el sistema. Para saber **qué** arreglar hay que ver **cómo** falla.
#
# La **matriz de confusión** cruza la categoría real (filas) con la predicha (columnas). La diagonal
# son los aciertos; todo lo que queda fuera de la diagonal son confusiones.
#
# De la matriz salen dos métricas por clase $c$:
#
# $$\text{precision}(c) = \frac{TP}{TP + FP} \qquad\qquad \text{recall}(c) = \frac{TP}{TP + FN}$$
#
# - **TP** (verdadero positivo): era $c$ y predijo $c$.
# - **FP** (falso positivo): predijo $c$, pero era otra clase.
# - **FN** (falso negativo): era $c$, pero predijo otra clase.
#
# En palabras: **precision** responde *"cuando predice $c$, ¿qué parte de las veces acierta?"* y
# **recall**, *"de todos los casos que eran $c$, ¿qué parte detecta?"*. Una clase con recall alto y
# precision baja se está usando como **cajón de sastre**: el modelo mete ahí casos de otras clases.

# %%
clases = sorted(L.CATEGORIAS)
corto = {"aplicacion": "aplic", "datos": "datos", "infraestructura": "infra",
         "seguridad": "segur", "spam": "spam"}
matriz = {real: Counter() for real in clases}
for real, predicho in v1["pares"]:
    matriz[real][predicho] += 1

print("Matriz de confusión · filas = real, columnas = predicho · %d predicciones" % len(v1["pares"]))
print("")
print("  %-16s" % "real / predicho" + "".join("%7s" % corto[c] for c in clases) + "   ilegible")
for real in clases:
    ilegibles = sum(v for p, v in matriz[real].items() if p not in clases)
    print("  %-16s" % real + "".join("%7d" % matriz[real][c] for c in clases) + "%11d" % ilegibles)

# %% [markdown]
# **Cómo leer la matriz:** cada fila reparte las predicciones de una categoría real. La diagonal son
# aciertos. Busca la **celda más alta fuera de la diagonal**: es la confusión que más nota te cuesta y la
# primera que hay que atacar en el prompt, por ejemplo con una regla de desempate entre esas dos clases.
# La columna *ilegible* cuenta las respuestas que no se pudieron parsear como JSON.
#
# Ahora, precision y recall por clase:

# %%
print("  %-16s %10s %8s %9s" % ("clase", "precision", "recall", "soporte"))
precisiones = []
for c in clases:
    tp = sum(1 for r, p in v1["pares"] if r == c and p == c)
    fp = sum(1 for r, p in v1["pares"] if r != c and p == c)
    fn = sum(1 for r, p in v1["pares"] if r == c and p != c)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    precisiones.append((precision, c))
    print("  %-16s %10.2f %8.2f %9d" % (c, precision, recall, tp + fn))

peor_precision, clase_peor = min(precisiones)
print("")
print("Clase con menor precision: %s (%.2f). Ahí el modelo mete casos de otras clases." % (clase_peor, peor_precision))

# %% [markdown]
# **Cómo leer la tabla:** el **soporte** es el número de predicciones cuyo valor real es esa clase
# (casos × 3 corridas). Con poco soporte, la precision y el recall de esa clase son poco fiables: mira spam.
#
# El mismo análisis, resumido en palabras:

# %%
donde_se_equivoca(v1, top=3)

# %% [markdown]
# **Lo que te llevas:** la nota global dice **cuánto** falla; la matriz y precision/recall dicen **qué**
# arreglar primero.

# %% [markdown]
# ---
# ## Paso 5 · Comparar versiones: regresiones por grupo, señal o ruido
#
# **El prompt es un artefacto versionado.** Cada versión es un archivo en `prompts/` con su plantilla,
# modelo, temperatura y formato de salida. Nunca se sobrescribe la anterior: así puedes comparar notas
# entre versiones y hacer *rollback* (volver a la versión anterior) con un cambio de configuración (diapositiva 23).
#
# La v2 añade a la v1 una rúbrica de severidad, una regla de desempate y dos ejemplos resueltos
# (*few-shot*). Este es el diff:

# %%
PROMPT_V2 = L.cargar_prompt("clasificar_incidente.v2.yaml")
lineas_v1 = set(PROMPT_V1["plantilla"].splitlines())
nuevas = [l for l in PROMPT_V2["plantilla"].splitlines() if l.strip() and l not in lineas_v1]
print("Líneas añadidas en la v2 (%d):" % len(nuevas))
print("")
for l in nuevas:
    print("  + " + l)

# %%
v2 = correr_eval("clasificar_incidente.v2.yaml", etiqueta="prompt v2")
comparar_versiones(v1, v2)

# %% [markdown]
# **Cómo leer la comparación**
#
# - **Nota global:** la rúbrica y el few-shot reducen la ambigüedad, y la nota sube.
# - **Por dificultad:** la mejora no es uniforme. Compara cuánto suben los típicos y cuánto los
#   difíciles: mejorar las instrucciones arregla antes los casos claros.
# - **Por categoría:** la media global puede subir mientras una categoría baja. Es un efecto de la
#   agregación: la media pondera por número de casos, y una categoría con 2 casos pesa solo el 5%.
#
# ### ¿Señal o ruido?
#
# Antes de declarar una regresión, compara la bajada con la **resolución** del paso 2. Si una
# categoría baja exactamente un salto mínimo, el cambio equivale a **un solo campo en un solo caso**:
# con esa cobertura no puedes concluir que la versión nueva sea peor.

# %%
print("Bajadas por categoría, medidas en saltos mínimos de resolución:")
print("")
hay_bajadas = False
for categoria, n in sorted(por_categoria.items()):
    grupo = "cat:" + categoria
    delta = v2["por_grupo"][grupo] - v1["por_grupo"][grupo]
    resolucion = 1 / (n * len(CAMPOS))
    if delta < -0.005:
        hay_bajadas = True
        saltos = -delta / resolucion
        print("  %-16s baja %.3f = %.1f %s de resolución (%.3f), con %d casos"
              % (categoria, -delta, saltos, "salto" if round(saltos, 1) == 1.0 else "saltos", resolucion, n))
if not hay_bajadas:
    print("  Ninguna categoría baja.")

# %% [markdown]
# ---
# ## Paso 6 · Validar la métrica: romper el prompt a propósito
#
# ¿Cómo sabes que tu eval **detecta** algo? Con la idea del *mutation testing*: introduces un defecto
# conocido y compruebas que la métrica lo detecta. Si la nota no baja, la métrica es **decorativa**
# (diapositiva 28).
#
# La v3 tiene **tres defectos a la vez**: instrucciones mínimas, `temperature = 0.9` y no exige JSON.

# %%
PROMPT_V3 = L.cargar_prompt("clasificar_incidente.v3_roto.yaml")
print("Plantilla de la v3:")
print("")
for linea in PROMPT_V3["plantilla"].splitlines():
    print("  " + linea)
print("  ({{ticket}} es la variable donde se inserta el texto de cada ticket)")
print("")
print("temperature: %s   (v1: %s)" % (PROMPT_V3["temperature"], PROMPT_V1["temperature"]))
print("formato_json: %s   (v1: %s)" % (PROMPT_V3["formato_json"], PROMPT_V1["formato_json"]))

# %%
v3 = correr_eval("clasificar_incidente.v3_roto.yaml", etiqueta="prompt v3 (roto)")
comparar_versiones(v1, v3)

caida = v1["score_global"] - v3["score_global"]
print("")
if caida > 0.10:
    print("VEREDICTO: la nota global cae %.2f. La métrica detecta el defecto: es válida." % caida)
else:
    print("VEREDICTO: la nota casi no cambia. La métrica no detecta el defecto: es decorativa.")

# %% [markdown]
# **Cómo leer el resultado**
#
# - **JSON válido** se desploma: sin la instrucción de devolver solo JSON, el modelo envuelve la respuesta
#   en texto (*"Claro, aquí tienes..."*) y el parseo falla. Es un fallo de **forma**.
# - **La nota global** se hunde: fallos de forma más fallos de **contenido**.
# - **Límite del experimento:** con tres defectos a la vez no puedes atribuir la caída a uno solo. En un
#   experimento real se cambia **una variable cada vez** (*ablation*): primero solo la temperatura, luego
#   solo el formato, etc.
#
# ### EJERCICIO 2 · Un gate de regresión con tolerancia por grupo
#
# En la sesión 3 esta comparación se automatiza en el pipeline de CI (integración continua) como un **gate**: bloquea el cambio si la calidad
# empeora. La regla que vamos a usar: **ningún grupo puede bajar más de `caida_maxima`**, aunque la nota
# global suba.
#
# Completa `decidir()` para que devuelva `"BLOQUEAR"` si algún grupo baja más de `caida_maxima`, y
# `"PASA"` si no.

# %%
def decidir(antes, despues, caida_maxima=0.05):
    bajadas = []
    for grupo, nota_despues in despues["por_grupo"].items():
        nota_antes = antes["por_grupo"][grupo]
        # TODO: si (nota_antes - nota_despues) es mayor que caida_maxima, añade `grupo` a `bajadas`
    return "BLOQUEAR" if bajadas else "PASA"

print("v1 -> v3 (roto):", decidir(v1, v3))
print("v1 -> v2       :", decidir(v1, v2))
print("")
if decidir(v1, v3) != "BLOQUEAR":
    print("Todavía no: el prompt roto tiene que salir BLOQUEAR.")
elif decidir(v1, v2) == "BLOQUEAR":
    print("OK. La v2 también sale BLOQUEAR, aunque su nota global es mejor.")
    print("Mira el paso 5: la bajada que la bloquea es de un salto mínimo en una categoría de 2 casos.")
    print("Un gate así da falsos positivos. Dos arreglos posibles: más casos de esa categoría,")
    print("o una tolerancia que tenga en cuenta la resolución de cada grupo.")
else:
    print("OK: el prompt roto se bloquea y la v2 pasa.")

# %% [markdown]
# ---
# ## Paso 7 · LLM-as-judge: evaluar sin respuesta exacta
#
# Hasta ahora había ground truth estructurado y bastaba con comparar campos. Si el sistema **genera
# texto libre** (un resumen, un correo, un postmortem), no hay comparación exacta posible. Entonces se
# usa **otro modelo como evaluador**: el *LLM-as-judge*.
#
# Dos formas de usarlo:
#
# - **Pointwise:** el juez pone una nota a una respuesta, por ejemplo de 1 a 5 con una rúbrica.
# - **Pairwise:** el juez compara dos respuestas y elige la mejor. Es lo que haremos aquí.
#
# Un juez **también es un modelo**, así que tiene sesgos sistemáticos (diapositiva 26):
#
# | Sesgo | Qué hace | Control |
# |---|---|---|
# | **Posición** | Prefiere la respuesta que aparece primero | Evaluar en los dos órdenes (*swap test*) |
# | **Longitud** (*verbosity*) | Prefiere la respuesta más larga | Rúbrica explícita que no premie la extensión |
# | **Autoafinidad** (*self-preference*) | Prefiere texto de su misma familia de modelos | Usar un juez de otro proveedor |
#
# Y la regla más importante: **un juez se valida antes de usarlo**, comparando sus decisiones con
# juicios humanos. Si el acuerdo no llega al **80%**, todavía no sirve.
#
# **Montaje del experimento:** 20 pares en los que la respuesta correcta es conocida. La buena es
# **corta y correcta**; la mala es **larga y equivocada**. Una persona acertaría los 20, así que el
# acuerdo con el humano es simplemente el acierto del juez.

# %%
def buena_y_mala(caso):
    correcta = caso["esperado"]
    buena = json.dumps(correcta, ensure_ascii=False)
    equivocada = dict(correcta, severidad="media",
                      categoria="aplicacion" if correcta["categoria"] != "aplicacion" else "datos")
    mala = ("Tras un analisis detallado del ticket y considerando el impacto potencial "
            "sobre los distintos equipos implicados, la valoracion mas prudente y "
            "completa que puedo ofrecer es la siguiente: " + json.dumps(equivocada, ensure_ascii=False) +
            " Espero que esta explicacion resulte de utilidad para el equipo.")
    return buena, mala

PARES = [(c,) + buena_y_mala(c) for c in CASOS[:20]]

JUEZ_INGENUO = """Eres un juez de calidad. Puntua cual de las dos respuestas clasifica
mejor el ticket. Responde SOLO con JSON: {"ganador": "A" o "B"}.

Ticket: {{ticket}}

Respuesta A: {{a}}
Respuesta B: {{b}}"""

def preguntar_al_juez(rubrica, caso, a, b):
    variables = {"ticket": caso["entrada"], "a": a, "b": b}
    if "{{referencia}}" in rubrica:
        variables["referencia"] = json.dumps(caso["esperado"], ensure_ascii=False)
    r = chat(L.render(rubrica, **variables), modelo="sim-large", temperature=0, prompt_id="juez")
    try:
        return r.json().get("ganador")
    except Exception:
        return None

caso, buena, mala = PARES[0]
print("Un par del experimento:")
print("")
print("  buena:", buena)
print("  mala: ", mala[:105] + "...")
print("")
con_buena_en_a = preguntar_al_juez(JUEZ_INGENUO, caso, buena, mala)
con_buena_en_b = preguntar_al_juez(JUEZ_INGENUO, caso, mala, buena)
print("  Orden 1 (buena = A): el juez elige %s   (correcto: A)" % con_buena_en_a)
print("  Orden 2 (buena = B): el juez elige %s   (correcto: B)" % con_buena_en_b)
print("")
if con_buena_en_a == con_buena_en_b:
    print("  Elige la misma letra en los dos órdenes: decide por posición, no por contenido.")
elif con_buena_en_a == "A" and con_buena_en_b == "B":
    print("  Acierta en los dos órdenes. Veamos los 20 pares.")
else:
    print("  Falla en los dos órdenes: prefiere la respuesta larga.")

# %% [markdown]
# Un par no es una muestra. Ahora los 20 pares, en los dos órdenes, con tres métricas:
#
# - **Acierto con la buena en A** y **acierto con la buena en B**: si difieren mucho, hay sesgo de posición.
# - **Consistencia al intercambiar el orden**: qué parte de los pares recibe **el mismo veredicto sobre el
#   contenido** en los dos órdenes, acierte o no. Un juez que decide por posición es inconsistente.

# %%
def medir_juez(rubrica):
    en_a = en_b = consistentes = 0
    for c, b, m in PARES:
        orden_1 = preguntar_al_juez(rubrica, c, b, m)      # buena en A
        orden_2 = preguntar_al_juez(rubrica, c, m, b)      # buena en B
        en_a += orden_1 == "A"
        en_b += orden_2 == "B"
        consistentes += (orden_1 == "A") == (orden_2 == "B")
    n = len(PARES)
    metricas = {"acierto_buena_en_A": en_a / n, "acierto_buena_en_B": en_b / n,
                "consistencia": consistentes / n}
    print("  Acierto con la buena en A:        %3.0f%%  %s" % (100 * en_a / n, barra(en_a / n, 20)))
    print("  Acierto con la buena en B:        %3.0f%%  %s" % (100 * en_b / n, barra(en_b / n, 20)))
    print("  Consistencia al intercambiar:     %3.0f%%  %s" % (100 * consistentes / n, barra(consistentes / n, 20)))
    return metricas

def veredicto_juez(m):
    peor = min(m["acierto_buena_en_A"], m["acierto_buena_en_B"])
    if peor >= 0.8 and m["consistencia"] >= 0.8:
        return "Validado: acierto >= 80% en los dos órdenes y consistente."
    return "No validado: el acierto depende del orden. No puede usarse en un gate."

print("Juez ingenuo:")
m_ingenuo = medir_juez(JUEZ_INGENUO)
print("")
print(veredicto_juez(m_ingenuo))

# %% [markdown]
# **Cómo leer el resultado:** el juez ingenuo acierta bastante con la buena en A y nada con la buena
# en B. No evalúa el contenido: se deja llevar por la posición y por la longitud. Además, su **consistencia
# es baja**: sobre el mismo par cambia de veredicto solo porque cambia el orden.
#
# ### Controles sobre el juez
#
# Aplicamos tres controles en la rúbrica:
#
# 1. **Reference-guided grading:** se le da el ground truth como referencia. El juez deja de opinar y
#    pasa a comparar.
# 2. **Neutralizar la posición:** se le indica que el orden es aleatorio.
# 3. **Neutralizar la longitud:** se le indica que la extensión no suma puntos.

# %%
JUEZ_CORREGIDO = """Eres un juez de calidad. Criterio unico: que respuesta coincide mejor
con la respuesta de referencia. El orden es aleatorio, ignora la posicion.
Penaliza el relleno: la extension no suma puntos.
Responde SOLO con JSON: {"ganador": "A" o "B"}.

Ticket: {{ticket}}
Respuesta de referencia: {{referencia}}

Respuesta A: {{a}}
Respuesta B: {{b}}"""

print("Juez corregido:")
m_corregido = medir_juez(JUEZ_CORREGIDO)
print("")
print(veredicto_juez(m_corregido))

# %% [markdown]
# ### EJERCICIO 3 · ¿Qué control es el que importa?
#
# Aplicamos tres controles a la vez, así que no sabemos cuál hace el trabajo: es el mismo problema de
# atribución del paso 6. Hagamos una ablación de uno de ellos.
#
# Abajo tienes una copia del juez corregido. **Borra la línea** `Respuesta de referencia: {{referencia}}`
# y vuelve a ejecutar la celda. Antes, apuesta: ¿cuánto baja el acierto?

# %%
MI_JUEZ = """Eres un juez de calidad. Criterio unico: que respuesta coincide mejor
con la respuesta de referencia. El orden es aleatorio, ignora la posicion.
Penaliza el relleno: la extension no suma puntos.
Responde SOLO con JSON: {"ganador": "A" o "B"}.

Ticket: {{ticket}}
Respuesta de referencia: {{referencia}}

Respuesta A: {{a}}
Respuesta B: {{b}}"""

print("Tu juez:")
m_mio = medir_juez(MI_JUEZ)
print("")
if "{{referencia}}" in MI_JUEZ:
    print("Todavía no has borrado la línea de la respuesta de referencia.")
elif min(m_mio["acierto_buena_en_A"], m_mio["acierto_buena_en_B"]) < 0.8:
    print("Eso es: sin el ground truth como referencia, el juez vuelve a decidir por la forma.")
    print("Las instrucciones sobre orden y longitud, solas, no bastan: el control que importa es la referencia.")
    if m_mio["consistencia"] >= 0.8:
        print("")
        print("Y fíjate en la consistencia: sigue alta. Se equivoca siempre igual, eligiendo la respuesta larga.")
        print("Consistente no es lo mismo que correcto: por eso se miden las dos cosas.")
else:
    print("Sigue validado. Vuelve a ejecutar la celda y compara.")

# %% [markdown]
# ---
# ## Resumen técnico
#
# | Concepto | Qué comprobaste | Diapositiva |
# |---|---|---|
# | Parseo, validación de esquema y acierto por campo | Forma y contenido fallan por separado y se miden por separado | 25 |
# | Golden set estratificado | Casos reales, mezcla 60/30/10 y cobertura por categoría | 24 |
# | Resolución de la métrica | Con $n$ casos, la nota de un grupo se mueve a saltos de $1/(4n)$ | 24 |
# | Varias corridas y reproducibilidad | Nota guardada con `prompt_id`, modelo y `commit` | 27 |
# | Matriz de confusión, precision y recall | Qué clase se confunde con cuál, y dónde actuar | 25 |
# | Prompt versionado y regresión por grupo | La media sube mientras un grupo baja; hay que distinguir señal de ruido | 23 y 27 |
# | Mutation testing de la métrica | Si un defecto conocido no baja la nota, la métrica es decorativa | 28 |
# | LLM-as-judge | Sesgo de posición y de longitud; validación con al menos 80% de acuerdo humano | 26 |
#
# ### Tarea para la próxima sesión
#
# 1. Construye tu golden set: **20 a 30 casos reales** con ground truth escrito por quien hace hoy ese
#    trabajo, en el mismo formato que `datos/golden_incidentes.jsonl`.
# 2. Revisa la cobertura: ninguna categoría con menos de 3 casos.
# 3. Corre el eval con tu prompt actual y **guarda la nota base** con su `commit`: en la sesión 3 esa
#    nota se defiende con un gate.
