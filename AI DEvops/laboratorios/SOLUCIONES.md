# Soluciones de los ejercicios

Miralas **despues** de intentarlo. Casi todos los ejercicios tienen mas de una
solucion valida: estas son las mas cortas, no las unicas.

---

## Sesion 1

### Ejercicio 1 - Respuesta mayoritaria (self-consistency)

```python
def respuesta_mayoritaria(prompt, n=10, temperatura=0.7):
    votos = Counter()
    for _ in range(n):
        r = chat(prompt, modelo=MODELO, temperature=temperatura, formato_json=True)
        try:
            votos[r.json()["categoria"]] += 1
        except Exception:
            votos["_invalida_"] += 1
    if not votos:
        return None, 0, n
    cat, v = votos.most_common(1)[0]
    return cat, v, n
```

Con `temperature=0` casi siempre salen 1 o 2 respuestas distintas de 20. No es cero:
esa es la diferencia entre *casi repetible* y *repetible*.

### Ejercicio 2 - Esquema con rangos

```python
def validar(d, esquema=ESQUEMA):
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
            errores.append("'%s' deberia ser %s" % (campo, regla["tipo"].__name__))
            continue
        if "valores" in regla and v not in regla["valores"]:
            errores.append("'%s'='%s' fuera de %s" % (campo, v, regla["valores"]))
        if "minimo" in regla and v < regla["minimo"]:
            errores.append("'%s'=%s por debajo de %s" % (campo, v, regla["minimo"]))
        if "maximo" in regla and v > regla["maximo"]:
            errores.append("'%s'=%s por encima de %s" % (campo, v, regla["maximo"]))
    return errores

ESQUEMA_V2 = dict(ESQUEMA)
ESQUEMA_V2["confianza"] = {"tipo": float, "minimo": 0.0, "maximo": 1.0, "obligatorio": True}
```

### Ejercicio 3 - Podar el contexto

```python
def fragmento_relevante(doc, consulta, max_tokens=300):
    secciones = ["## " + s for s in doc.split("## ") if s.strip()]
    palabras = set(w for w in L._norm(consulta).split() if len(w) > 4)
    def puntua(s):
        return len(palabras & set(L._norm(s).split()))
    mejor = max(secciones, key=puntua)
    return mejor[: max_tokens * 4]
```

### Ejercicio 4 - Bucle con terminacion explicita

```python
def plan_bueno(estado):
    if estado["pasos"] == 0:
        return {"herramienta": "buscar_logs", "argumento": "pagos-api"}
    if estado["pasos"] == 1:
        return {"herramienta": "reiniciar_pod", "argumento": "pagos-api"}
    return None          # criterio de terminacion explicito
```

`bucle(plan_bueno)["parada"]` devuelve `"tarea completada"`, no un tope. Esa es la
diferencia entre un agente que termina y uno que se queda sin presupuesto.

### Ejercicio 5 - Nodo de notificacion

```python
def nodo_notificar(s):
    s.recorrido.append("(aviso enviado a la guardia)")
    return s

def ruta_tras_enriquecer(s):
    if s.clasificacion["severidad"] == "critica":
        return "notificar"
    return "aprobacion_humana" if s.clasificacion.get("requiere_humano") else "cerrar"

GRAFO["notificar"] = (
    nodo_notificar,
    lambda s: "aprobacion_humana" if s.clasificacion.get("requiere_humano") else "cerrar")
```

Fijate en lo que **no** tuviste que tocar: ningun otro nodo. Eso es la ventaja del grafo.

### Ejercicio 6 - Umbral del router

No hay un numero universal. El criterio si lo hay: **el umbral mas bajo que mantiene la
exactitud dentro de un punto de la del modelo grande**. Si dos umbrales empatan en
exactitud, gana el barato. Y si el ahorro exige perder exactitud en la clase de
seguridad, no es un ahorro: es un riesgo mal contabilizado.

---

## Sesion 2

### Ejercicio 1 - Auditar el set dorado

```python
def auditar(casos):
    avisos = []
    cat = Counter(c["esperado"]["categoria"] for c in casos)
    for k, v in cat.items():
        if v < 3:
            avisos.append("la categoria '%s' solo tiene %d casos: no podras medirla" % (k, v))
    dificiles = sum(1 for c in casos if c["dificultad"] == "dificil") / len(casos)
    if dificiles < 0.20:
        avisos.append("solo el %.0f%% son dificiles: el set es demasiado facil" % (100 * dificiles))
    vistos, dup = set(), 0
    for c in casos:
        clave = " ".join(c["entrada"].lower().split())
        dup += clave in vistos
        vistos.add(clave)
    if dup:
        avisos.append("%d casos duplicados: inflan el puntaje sin aportar informacion" % dup)
    return avisos
```

### Ejercicio 2 - Guardar y comparar

Estan resueltos en `evaluador.py` (`guardar` y `comparar`). Lo importante:

```python
def comparar(anterior, nuevo, caida_maxima=0.05):
    motivos = []
    for grupo, valor in nuevo["por_grupo"].items():
        antes = anterior["por_grupo"].get(grupo)
        if antes is not None and antes - valor > caida_maxima:
            motivos.append("%s cae %.3f (%.3f -> %.3f)" % (grupo, antes - valor, antes, valor))
    return ("BLOQUEAR" if motivos else "PASA"), motivos
```

Corre `comparar(base, mejor)` sobre v1 y v2: el global sube y aun asi la clase `spam`
baja. Un promedio estable esconde una clase rota.

### Ejercicio 4 - Juicio robusto al orden

```python
def juicio_robusto(ticket, buena, mala, referencia):
    g1 = juzgar(RUBRICA_BUENA, ticket, buena, mala, referencia)   # buena en A
    g2 = juzgar(RUBRICA_BUENA, ticket, mala, buena, referencia)   # buena en B
    if g1 == "A" and g2 == "B":
        return "buena"
    if g1 == "B" and g2 == "A":
        return "mala"
    return "empate"      # el juez se contradice: a revision humana
```

La tasa de `empate` **es** la medida del sesgo de posicion de tu juez.

---

## Sesion 3

### Ejercicio 1 - Arbol de trazas y campos faltantes

```python
def arbol(trace_id):
    spans = sorted([t for t in L.TRAZAS if t["trace_id"] == trace_id],
                   key=lambda t: t["timestamp"])
    print(trace_id)
    for t in spans:
        sangria = "  " if t["parent_span_id"] is None else "    "
        print("%s%-20s %5d ms  %.6f USD  %s"
              % (sangria, t["prompt_id"], t["latencia_ms"], t["costo_usd"], t["estado"]))

def campos_faltantes(traza):
    return [c for c in CAMPOS_OBLIGATORIOS if c not in traza]
```

### Ejercicio 2 - Informe del pipeline

```python
def informe_pr(anterior, nuevo, casos=CASOS):
    lineas = ["### Eval gate", "", "| metrica | antes | ahora | delta |", "|---|---|---|---|"]
    for m in ("score_global", "exactitud_categoria", "validez_esquema"):
        lineas.append("| %s | %.3f | %.3f | %+.3f |"
                      % (m, anterior[m], nuevo[m], nuevo[m] - anterior[m]))
    caidas = [(g, anterior["por_grupo"][g], v) for g, v in nuevo["por_grupo"].items()
              if g in anterior["por_grupo"] and anterior["por_grupo"][g] - v > 0.05]
    if caidas:
        lineas += ["", "**Grupos que caen mas de 0.05:**"]
        lineas += ["- `%s`: %.3f -> %.3f" % c for c in caidas]
    runs = max(1, len(nuevo["pares"]) // len(casos))
    fallos = [casos[i // runs]["id"] for i, (real, pred) in enumerate(nuevo["pares"])
              if real != pred]
    if fallos:
        lineas += ["", "**Casos que empeoraron:** " + ", ".join(sorted(set(fallos))[:3])]
    return "\n".join(lineas)
```

### Ejercicio 3 - Tercera senal del canario

```python
costos = {"activa": 0.0, "canario": 0.0}
# dentro del bucle, despues de atender:
costos[rama] += costo
media_act = costos["activa"] / max(1, len(metricas["activa"]))
media_can = costos["canario"] / max(1, len(metricas["canario"]))
if len(metricas["canario"]) >= 5 and media_can > media_act * 1.3:
    return {"corte_en_request": i, "motivo": "costo por tarea +30%"}
```

### Ejercicio 4 - Las cuatro alertas

```python
ALERTAS = {
    "costo_diario_sobre_presupuesto": lambda m: m["costo_dia_usd"] > m["presupuesto_dia_usd"],
    "caida_puntaje_online":           lambda m: m["score_base"] - m["score_online"] > 0.05,
    "salto_reintentos":               lambda m: m["reintentos"] > 3 * m["reintentos_base"],
    "p95_fuera_de_rango":             lambda m: m["p95_ms"] > m["p95_objetivo"],
}
```

Cual despierta a alguien: **caida de puntaje** y **costo**, porque no se arreglan solas.
El p95 y los reintentos avisan en el canal del equipo; si persisten 30 minutos, escalan.

---

## Sesion 4

### Ejercicio 1 - Costo por tarea resuelta

```python
def costo_por_tarea_resuelta(trazas, tareas_ok, tareas_a_humano, coste_humano=0.40):
    costo_modelo = sum(t["costo_usd"] for t in trazas)
    return (costo_modelo + tareas_a_humano * coste_humano) / max(1, tareas_ok)
```

El numero sube uno o dos ordenes de magnitud en cuanto entra el tiempo humano. Por eso
es **esta** unidad la que decide si el caso de uso cierra, y no el costo por request.

### Ejercicio 2 - Invalidacion y datos que no se cachean

```python
def invalidar(self, prompt_id):
    self.datos = {k: v for k, v in self.datos.items() if v[2] != prompt_id}

CAMPOS_PROHIBIDOS = ("documento", "tarjeta", "telefono", "direccion")

def no_cachear(ticket, ambito):
    if "rol:admin" in ambito:                 # respuestas con visibilidad ampliada
        return True
    return any(c in ticket.lower() for c in CAMPOS_PROHIBIDOS)
```

Como la clave es un hash del prompt, para poder invalidar por `prompt_id` hay que
guardarlo aparte: `self.datos[k] = (valor, ts, prompt_id)`.

### Ejercicio 3 - El coste del umbral flojo

Con 0,80 la tasa de acierto sube mucho y el puntaje del eval baja: estas sirviendo la
respuesta de otra pregunta. Es exactamente el mismo error que el recorte de prompt del
final del notebook, con otra cara.

### Ejercicio 5 - Fallos parciales en agentes

```python
POLITICA = "reintentar_paso"     # o "reiniciar_todo" o "entregar_parcial"

def ejecutar_con_politica(estado, inicio="clasificar", max_reintentos=2):
    actual, reintentos = inicio, 0
    while actual:
        fn, ruta = GRAFO[actual]
        try:
            estado = fn(estado)
        except Exception:
            if POLITICA == "reintentar_paso" and reintentos < max_reintentos:
                reintentos += 1
                continue                       # el mismo nodo, no todo el grafo
            if POLITICA == "entregar_parcial":
                estado.errores.append("fallo en %s, entrega parcial" % actual)
                return estado
            raise
        reintentos = 0
        actual = ruta(estado)
    return estado
```

Lo importante no es cual eliges: es **elegirla antes** del incidente.

---

## Sesion 5

### Ejercicio 1 - Gate de seguridad

```python
def gate_seguridad(fallos, maximo=0):
    if fallos > maximo:
        return False, "%d ataques pasan (maximo permitido: %d)" % (fallos, maximo)
    return True, "ok"
```

En seguridad el umbral es **cero**. Un 93% de ataques bloqueados no es un aprobado:
es una puerta abierta con estadistica encima.

Para meterlo en `ci_eval.py`, dentro de `evaluar_gate`:

```python
filas, fallos = correr_red_team(PROMPT_DEFENDIDO, ejecutor_seguro)
if fallos > 0:
    motivos.append("red team: %d ataques pasan" % fallos)
```

### Ejercicio 2 - Redaccion con excepciones

```python
EXCEPCIONES = (re.compile(r"\bINC-\d+\b"), re.compile(r"\bCASO-\d+\b"))

def redactar(texto):
    reservas = {}
    for i, patron in enumerate(EXCEPCIONES):           # protege lo que NO es PII
        for hallazgo in patron.findall(texto):
            marca = "<<%d_%d>>" % (i, len(reservas))
            reservas[marca] = hallazgo
            texto = texto.replace(hallazgo, marca)
    encontrados = {}
    for nombre, patron in PATRONES_PII.items():
        hallazgos = re.findall(patron, texto)
        if hallazgos:
            encontrados[nombre] = len(hallazgos)
            texto = re.sub(patron, "[" + nombre.upper() + "_REDACTADO]", texto)
    for marca, original in reservas.items():
        texto = texto.replace(marca, original)
    return texto, encontrados
```

Mide los falsos positivos corriendolo sobre el set dorado: cuenta cuantos casos salen
con algo redactado cuando no habia PII. Si son mas del 2%, tu regex es demasiado
agresiva y vas a degradar la calidad de las respuestas.

### Ejercicio 3 - El runbook

No tiene solucion de codigo. Si en tu runbook sigue poniendo "el equipo de plataforma"
en vez de un nombre y un apellido, el ejercicio no esta hecho.
