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

### Ejercicio 1 - ¿Hay categorías con muy pocos casos?

```python
def categorias_con_pocos_casos(casos, minimo=3):
    cuenta = Counter(c["esperado"]["categoria"] for c in casos)
    pocas = []
    for categoria, n in cuenta.items():
        if n < minimo:
            pocas.append(categoria)
    return pocas
```

Sale `['spam']`: solo tiene 2 casos, así que su **resolución** es 1 / (2 × 4) = 0,125. Un solo
campo que pasa de bien a mal mueve su nota ese salto entero. Vuelve a aparecer en el paso 5 y
en el Ejercicio 2.

### Ejercicio 2 - ¿Dejarías pasar este cambio?

```python
def decidir(antes, despues, caida_maxima=0.05):
    bajadas = []
    for grupo, nota_despues in despues["por_grupo"].items():
        nota_antes = antes["por_grupo"][grupo]
        if nota_antes - nota_despues > caida_maxima:
            bajadas.append(grupo)
    return "BLOQUEAR" if bajadas else "PASA"
```

El prompt roto sale `BLOQUEAR`. La v2 normalmente también: spam baja 0,125, que es exactamente
un salto de resolución (un campo en uno de sus 2 casos). Es un **falso positivo** del gate.
Dos arreglos posibles: añadir casos de spam al golden set, o usar una tolerancia por grupo que
no sea menor que su resolución, por ejemplo `max(0.05, 1 / (4 * n))`.

### Ejercicio 3 - ¿Cuál de los tres cambios es el que importa?

No hay código que escribir: se borra la línea `Respuesta de referencia: {{referencia}}`
de `MI_JUEZ` y se vuelve a ejecutar.

Es una **ablación**: quitas un control y mides el efecto. El acierto cae de 100% a alrededor
de 15% (buena en A) y 0% (buena en B). Lo que hace fiable al juez es darle el ground truth como
referencia (*reference-guided grading*); las instrucciones sobre orden y longitud, solas, no
bastan. La consistencia, en cambio, sigue alta (alrededor de 85%): el juez se equivoca siempre
igual, eligiendo la respuesta larga. Consistente no es lo mismo que correcto. Y si se borra solo "Penaliza el relleno", no cambia nada: sigue en 100%.

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

---

## Laboratorio · IA en el día a día de DevOps

Con un modelo real las respuestas cambian de una ejecución a otra y entre modelos.

### Ejercicio 1 - Su propio pipeline

No hay una respuesta fija. Lo interesante es discutir qué pasó con logs largos (cuánto recortó
`recortar_log`), si el modelo acertó sin el diff y qué datos tuvieron que quitar antes de
mandarlo. Si el log tiene secretos, es la oportunidad para hablar de enmascararlos antes de
cualquier llamada al modelo.

### Ejercicio 2 - ¿Qué modelo usar?

Los cuatro suelen encontrar la causa (falta `pg_config` porque la imagen `slim` no trae las
librerías de PostgreSQL). La diferencia está en el detalle, el tiempo y el costo: el modelo caro
cuesta varias veces más y tarda más, para un resultado parecido. Para diagnosticar pipelines
conviene un modelo barato; el caro se justifica en tareas con más razonamiento, como el agente.

### Ejercicio 3 - Si el agente actuara solo

Condiciones razonables para dejar que ejecute `kubectl rollout undo` sin aprobación:

- La acción se puede deshacer y tiene runbook.
- Hubo un despliegue de ese servicio justo antes del problema (si no, el rollback no arregla nada).
- Solo en servicios no críticos al principio, o solo en ciertos horarios.
- Después de actuar, verifica que el servicio se recuperó; si no, avisa a una persona y no
  sigue probando cosas.
- Todo queda registrado en el canal del incidente.

## Proyecto final · Copiloto DevOps

Resultados de la última corrida real (24 de septiembre), para que sepas qué esperar en clase:

| Métrica | Resultado | Notas |
|---|---|---|
| Ruteo | 12 de 12 | Llama 3.1 8B resolvió 11; solo escaló el mensaje de Slack que no era un incidente |
| Categoría de CI | 5 de 5 | Qwen3 Coder, con algún reintento de por medio |
| Seguridad | 2 de 2 | Detección determinista, no depende del modelo |
| Costo | $0.0022 por evento | $2.68 al mes con 40 eventos diarios |

El log de CI que se diagnostica en el bloque 4 se baja en vivo de un repositorio público que esté
fallando, así que **cambia en cada clase**. En las pruebas fueron logs de entre 100 KB y 2,4 MB
(hasta 620.000 tokens, que mandados enteros costarían $0,62 por diagnóstico) y el recorte los dejó
en unos 8 KB. El diagnóstico salió correcto en los dos casos.

Sobre la categoría que devuelve: es el punto flojo, y a propósito. Cuando un test falla porque falta
una fixture, el modelo puede decir `test`, `config` o `dependencia`, y las tres se pueden defender.
Esa discusión es el contenido del bloque, no un error a esconder: si el equipo no se pone de acuerdo
en las categorías, la evaluación no mide nada.

### Para discutir en clase

No hay ejercicio con respuesta en este notebook: el proyecto se recorre entero y lo que queda son
tres discusiones que valen más que cualquier TODO.

**La categoría del fallo de CI.** Cuando un test se cae porque falta una fixture, el modelo puede
decir `test`, `config` o `dependencia`, y las tres se pueden defender. Si el equipo no se pone de
acuerdo, la evaluación no mide nada. Esa es la parte difícil de un set dorado, y no la resuelve el
modelo.

**Hasta dónde dejar actuar al agente.** Hoy propone y espera aprobación. Para dejarlo ejecutar el
`kubectl rollout undo` solo, lo razonable es exigir: que la acción se pueda deshacer, que haya
runbook, que el despliegue sea reciente, que el servicio no sea crítico, y que después verifique si
se recuperó y avise a una persona si no.

**Qué modelo usar dónde.** El pequeño abierto resuelve el ruteo por veinte veces menos plata; el
grande se justifica en el agente, que es lo que más razonamiento pide. Con la tabla de trazas a la
vista, la conversación deja de ser de opiniones.
