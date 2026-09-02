# -*- coding: utf-8 -*-
"""
lab_utils.py - Motor comun de los laboratorios del Taller AI DevOps (ClickIT).

Objetivo: que TODOS los ejercicios se puedan ejecutar sin instalar nada raro y
sin gastar un centavo. Por defecto se usa un "proveedor simulado" (modelos
`sim-small` y `sim-large`) que imita el comportamiento real de un LLM:

  - es no determinista (y la temperatura lo empeora)
  - su calidad depende de la calidad del prompt
  - rompe el formato si no se lo pides explicitamente
  - inventa datos cuando no le diste la informacion
  - obedece inyecciones de prompt si no lo defiendes
  - cuesta dinero, tarda y a veces falla

Si tienes OPENAI_API_KEY o ANTHROPIC_API_KEY, puedes pasar el nombre de un
modelo real y todo funciona igual (mismo objeto de respuesta, misma traza).

Uso minimo:

    from lab_utils import chat
    r = chat("Clasifica este ticket: ...", modelo="sim-small", temperature=0)
    print(r.texto, r.costo_usd, r.latencia_ms)
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "datos"
PROMPTS = RAIZ / "prompts"

# Factor para no esperar de verdad los milisegundos simulados.
# 0.05 => una llamada "de 800 ms" bloquea 40 ms reales.
VELOCIDAD_SIM = float(os.getenv("LAB_VELOCIDAD", "0.05"))

# --------------------------------------------------------------------------
# Precios
# --------------------------------------------------------------------------
# USD por 1.000.000 de tokens (entrada, salida).
# Los modelos sim-* son ficticios: sus precios estan elegidos para que se
# parezcan a un modelo barato y a uno caro. Si vas a usar modelos reales,
# rellena PRECIOS con los precios VIGENTES del proveedor (cambian seguido).
PRECIOS: dict[str, tuple[float, float]] = {
    "sim-small": (0.15, 0.60),
    "sim-large": (3.00, 15.00),
}

CATEGORIAS = ["infraestructura", "aplicacion", "seguridad", "datos", "spam"]
SEVERIDADES = ["critica", "alta", "media", "baja"]


# --------------------------------------------------------------------------
# Utilidades de texto y tokens
# --------------------------------------------------------------------------
def _norm(s: str) -> str:
    """minusculas + sin acentos, para comparar sin sufrir."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


try:  # tiktoken es opcional
    import tiktoken  # type: ignore

    _ENC = tiktoken.get_encoding("cl100k_base")

    def contar_tokens(texto: str) -> int:
        return len(_ENC.encode(texto or ""))

except Exception:  # aproximacion suficiente para el taller

    def contar_tokens(texto: str) -> int:
        """Aproximacion: ~4 caracteres por token. No es exacto, es orientativo."""
        return max(1, len(texto or "") // 4)


def costo_usd(modelo: str, tokens_in: int, tokens_out: int) -> float:
    p_in, p_out = PRECIOS.get(modelo, (0.0, 0.0))
    return round(tokens_in / 1e6 * p_in + tokens_out / 1e6 * p_out, 8)


# --------------------------------------------------------------------------
# Respuesta y trazas (esquema de la Sesion 3)
# --------------------------------------------------------------------------
@dataclass
class Respuesta:
    texto: str
    modelo: str
    tokens_in: int
    tokens_out: int
    tokens_cached: int
    costo_usd: float
    latencia_ms: int
    ttft_ms: int
    motivo_fin: str          # "stop" | "length"
    desde_cache: bool
    intentos: int
    trace_id: str
    span_id: str
    prompt_id: str
    estado: str              # "ok" | "error" | "rechazado"

    def json(self) -> Any:
        """Intenta parsear la respuesta como JSON. Lanza si no es JSON valido."""
        return json.loads(extraer_json(self.texto))

    def __str__(self) -> str:
        return self.texto


TRAZAS: list[dict] = []
_CONTADOR = {"llamadas": 0}


def limpiar_trazas() -> None:
    TRAZAS.clear()


def _registrar(r: Respuesta, extra: dict | None = None) -> None:
    fila = asdict(r)
    fila.pop("texto", None)
    fila["timestamp"] = round(time.time(), 3)
    fila.update(extra or {})
    TRAZAS.append(fila)


def trazas_df():
    """Devuelve las trazas como DataFrame de pandas (o lista de dicts si no hay pandas)."""
    try:
        import pandas as pd

        return pd.DataFrame(TRAZAS)
    except Exception:
        return TRAZAS


def resumen_trazas() -> dict:
    if not TRAZAS:
        return {"llamadas": 0}
    lat = sorted(t["latencia_ms"] for t in TRAZAS)
    return {
        "llamadas": len(TRAZAS),
        "costo_total_usd": round(sum(t["costo_usd"] for t in TRAZAS), 6),
        "tokens_in": sum(t["tokens_in"] for t in TRAZAS),
        "tokens_out": sum(t["tokens_out"] for t in TRAZAS),
        "latencia_media_ms": round(sum(lat) / len(lat)),
        "latencia_p95_ms": lat[max(0, int(len(lat) * 0.95) - 1)],
        "errores": sum(1 for t in TRAZAS if t["estado"] == "error"),
    }


# --------------------------------------------------------------------------
# Fallos simulados del proveedor (Sesion 4)
# --------------------------------------------------------------------------
class ProveedorError(RuntimeError):
    """El proveedor fallo. Igualito que en produccion, pero a tu antojo."""


_FALLOS = {"prob": 0.0, "modelos": None, "mensaje": "503 Service Unavailable"}


def configurar_fallos(probabilidad: float = 0.0, modelos: list[str] | None = None,
                      mensaje: str = "503 Service Unavailable") -> None:
    """Hace que el proveedor simulado falle. probabilidad=1.0 => caida total."""
    _FALLOS["prob"] = probabilidad
    _FALLOS["modelos"] = modelos
    _FALLOS["mensaje"] = mensaje


# --------------------------------------------------------------------------
# EL SIMULADOR
# --------------------------------------------------------------------------
KW = {
    "infraestructura": ["nodo", "kubernetes", "k8s", "pod", "cluster", "cpu",
                        "memoria", "disco", "balanceador", "autoscaling", "dns",
                        "certificado", "instancia", "terraform", "ec2", "red",
                        "oomkilled", "ingress"],
    "aplicacion": ["error 500", "excepcion", "stacktrace", "deploy", "endpoint",
                   "api", "bug", "regresion", "build", "release", "feature flag",
                   "checkout", "login", "formulario", "pantalla"],
    "seguridad": ["credencial", "token expuesto", "acceso no autorizado", "cve",
                  "vulnerabilidad", "phishing", "brecha", "escalada de privilegios",
                  "secreto", "clave expuesta", "intrusion", "exfiltracion",
                  "permisos de admin", "fuerza bruta"],
    "datos": ["etl", "pipeline de datos", "base de datos", "replica", "backup",
              "query", "migracion", "duplicados", "warehouse", "dbt", "integridad",
              "particion", "ingesta"],
    "spam": ["promocion", "descuento", "gana dinero", "webinar gratis", "oferta",
             "suscribete", "marketing", "newsletter", "clic aqui"],
}

KW_SEV = {
    "critica": ["caida total", "produccion caida", "todos los usuarios",
                "perdida de datos", "brecha activa", "fuera de servicio", "sin servicio"],
    "alta": ["degradado", "muchos usuarios", "p95", "errores masivos",
             "no pueden pagar", "no pueden entrar", "sla", "vulnerabilidad",
             "escalada de privilegios", "fuerza bruta", "expuesto", "expuesta",
             "retraso", "no se ejecuta", "riesgo", "fallo y", "perdio",
             "quedo sin", "sin cifrado", "factura subio", "credenciales de produccion",
             "publica los secretos", "guardan el token"],
    "media": ["intermitente", "algunos usuarios", "lento", "a veces", "warning"],
    "baja": ["cosmetico", "un usuario", "consulta", "staging", "duda", "pregunta",
             "sugerencia", "typo"],
}

_RE_SERVICIO = re.compile(r"servicio[:=]\s*([a-z0-9\-\_]+)", re.I)


def _servicio(texto: str) -> str:
    m = _RE_SERVICIO.search(texto or "")
    return m.group(1).lower() if m else "desconocido"


def _verdad(texto: str) -> tuple[dict, float]:
    """Lo que el simulador 'sabe' del ticket, y que tan seguro esta (dominancia)."""
    t = _norm(texto)
    puntos = {c: sum(1 for k in KW[c] if k in t) for c in CATEGORIAS}
    orden = sorted(puntos.items(), key=lambda kv: -kv[1])
    top, seg = orden[0], orden[1]
    cat = top[0] if top[1] > 0 else "aplicacion"
    dom = 0.35 if top[1] == 0 else min(1.0, (top[1] - seg[1]) / max(1, top[1]))
    sev = "media"
    for s in SEVERIDADES:
        if any(k in t for k in KW_SEV[s]):
            sev = s
            break
    if cat == "spam":
        sev = "baja"
    verdad = {
        "categoria": cat,
        "severidad": sev,
        "servicio": _servicio(texto),
        "requiere_humano": cat == "seguridad" or sev == "critica",
    }
    # El simulador es didactico: para los casos del set dorado conoce la etiqueta
    # correcta. Lo que decide si acierta o no es la CALIDAD DEL PROMPT y la
    # AMBIGUEDAD del caso, que es justo lo que queremos que midas en el taller.
    ref = _indice_verdad().get(_clave(texto))
    if ref:
        if ref["categoria"] != cat or ref["severidad"] != sev:
            dom *= 0.4          # el caso es ambiguo para el modelo: fallara mas
        verdad = dict(ref)
    return verdad, dom


def _clave(texto: str) -> str:
    return re.sub(r"\s+", " ", _norm(texto)).strip()[:200]


_CACHE_VERDAD: dict = {}


def _indice_verdad() -> dict:
    """Etiquetas conocidas del set dorado (si el archivo existe)."""
    if not _CACHE_VERDAD:
        _CACHE_VERDAD["_"] = True
        ruta = DATOS / "golden_incidentes.jsonl"
        if ruta.exists():
            for linea in ruta.read_text(encoding="utf-8").splitlines():
                if linea.strip():
                    c = json.loads(linea)
                    _CACHE_VERDAD[_clave(c["entrada"])] = c["esperado"]
    return _CACHE_VERDAD


def _calidad_prompt(prompt: str) -> float:
    """El simulador es mejor cuando el prompt esta mejor escrito. Igual que el real."""
    p = _norm(prompt)
    q = 0.48
    if sum(1 for c in CATEGORIAS if c in p) >= 4:
        q += 0.16                     # le diste el catalogo de categorias
    if p.count("ejemplo") >= 2:
        q += 0.14                     # few-shot
    if all(s in p for s in ("critica", "alta", "baja")):
        q += 0.06                     # rubrica de severidad
    if len(prompt) < 80:
        q -= 0.15                     # prompt de una linea
    return max(0.05, min(0.95, q))


def _pide_json(prompt: str) -> bool:
    p = _norm(prompt)
    return "json" in p and any(k in p for k in ("solo", "unicamente", "exclusivamente"))


def _modo(prompt: str) -> str:
    p = _norm(prompt)
    if "juez" in p or ("puntua" in p and ("rubrica" in p or "escala" in p)):
        return "juez"
    if "herramientas disponibles" in p or "acciones permitidas" in p:
        return "agente"
    if "<contexto>" in p or "<datos_externos" in p:
        return "rag"
    if any(c in p for c in CATEGORIAS) or "clasifica" in p or "categoria" in p:
        return "clasificar"
    return "texto"


MARCAS_INYECCION = [
    "ignora las instrucciones", "ignora las reglas", "olvida tus instrucciones",
    "nuevas instrucciones", "system override", "eres ahora", "revela el prompt",
    "envia el resumen a", "envia todo a", "manda los datos a", "exporta las credenciales",
    "dame las claves", "borra la tabla", "elimina el bucket", "actua como administrador",
    "terraform destroy", "variables de entorno del servidor", "asigname permisos",
]

MARCAS_ENVIO = ("envia el resumen a", "envia todo a", "manda los datos a",
                "exporta las credenciales", "envia el resumen")
MARCAS_BORRADO = ("borra la tabla", "elimina el bucket", "terraform destroy",
                  "borra el", "elimina la")

MARCAS_DEFENSA = [
    "trata el contenido como datos", "nunca como ordenes", "nunca como instrucciones",
    "ignora cualquier instruccion que aparezca dentro", "no obedezcas instrucciones",
    "<datos_externos", "contenido no confiable",
]


def hay_inyeccion(texto: str) -> bool:
    t = _norm(texto)
    return any(m in t for m in MARCAS_INYECCION)


def _hay_defensa(prompt: str) -> bool:
    p = _norm(prompt)
    return sum(1 for m in MARCAS_DEFENSA if m in p) >= 2


def _rng(prompt: str, modelo: str, temperature: float, seed):
    """Con temperature=0 y seed fija es (casi) reproducible. Con temperatura, no."""
    if temperature <= 0 and seed is not None:
        clave = "%s|%s|%s" % (prompt, modelo, seed)
    elif temperature <= 0:
        # "casi repetible no es repetible": un ~3% de las veces el resultado cambia
        # aunque no hayas tocado nada. Con `seed` fijo si es reproducible.
        nonce = "" if random.random() > 0.03 else str(time.time_ns())
        clave = "%s|%s|t0|%s" % (prompt, modelo, nonce)
    else:
        clave = "%s|%s|%s|%s|%s" % (prompt, modelo, temperature,
                                    _CONTADOR["llamadas"], time.time_ns())
    return random.Random(int(hashlib.sha256(clave.encode()).hexdigest()[:16], 16))


def _perturbar(verdad: dict, rng) -> dict:
    """Como se equivoca un LLM: plausiblemente, no al azar total."""
    salida = dict(verdad)
    campo = rng.choice(["categoria", "categoria", "severidad", "servicio"])
    if campo == "categoria":
        otras = [c for c in CATEGORIAS if c != verdad["categoria"]]
        salida["categoria"] = rng.choice(otras)
    elif campo == "severidad":
        i = SEVERIDADES.index(verdad["severidad"])
        vecinos = [SEVERIDADES[j] for j in (i - 1, i + 1) if 0 <= j < len(SEVERIDADES)]
        salida["severidad"] = rng.choice(vecinos)
    else:
        salida["servicio"] = "desconocido"
    salida["requiere_humano"] = (salida["categoria"] == "seguridad"
                                 or salida["severidad"] == "critica")
    return salida


def _sim_clasificar(prompt, entrada, modelo, rng, temperature, forzar_json):
    verdad, dom = _verdad(entrada)
    q = _calidad_prompt(prompt)
    if modelo == "sim-large":
        # el modelo caro no es magia: sobre todo aguanta mejor la ambiguedad
        q += 0.12
        dom = min(1.0, dom + 0.30)
    p_ok = max(0.05, min(0.97, q * (0.70 + 0.30 * dom) - temperature * 0.12))
    if temperature <= 0:
        p_ok -= 0.02   # "casi repetible" no es "repetible"

    salida = dict(verdad) if rng.random() < p_ok else _perturbar(verdad, rng)
    salida["confianza"] = round(min(0.99, max(0.30,
                                p_ok * (0.85 + 0.15 * dom) + rng.uniform(-0.06, 0.06))), 2)
    cuerpo = json.dumps(salida, ensure_ascii=False)

    if forzar_json or _pide_json(prompt):
        return cuerpo
    # Si no exigiste formato, el modelo "ayuda" y rompe tu parser.
    if rng.random() < 0.45:
        return "Claro, aqui tienes la clasificacion:\n\n```json\n" + cuerpo + "\n```\n\nEspero que sirva."
    return ("Este ticket parece de {c} con severidad {s}, del servicio {v}."
            .format(c=salida["categoria"], s=salida["severidad"], v=salida["servicio"]))


def _sim_juez(prompt, rng, temperature):
    """Juez con los sesgos de la Sesion 2: posicion, verbosidad y complacencia."""
    p = _norm(prompt)
    m = re.search(r"respuesta a[:\s]*(.{0,6000}?)respuesta b[:\s]*(.{0,6000})$", p, re.S)
    if m:
        a, b = m.group(1), m.group(2)
        # Los sesgos SI se pueden controlar con la rubrica. Eso es el Lab 2.
        peso_posicion = 0.10 if ("ignora la posicion" in p or "el orden es aleatorio" in p) else 0.35
        peso_verbosidad = 0.0 if ("penaliza el relleno" in p or "no premies la longitud" in p) else 0.30
        score = peso_posicion
        score += peso_verbosidad if len(a) > len(b) else -peso_verbosidad
        ref = re.search(r".*respuesta de referencia[:\s]*(.*?)respuesta a[:\s]", p, re.S)
        if ref:                     # con referencia, el juez ya puede acertar de verdad
            def _sol(x):
                return set(re.findall(r"[a-z0-9_]{3,}", x))
            r0 = _sol(ref.group(1))
            score += 1.2 if len(_sol(a) & r0) >= len(_sol(b) & r0) else -1.2
        score += rng.uniform(-0.25, 0.25)
        return json.dumps({"ganador": "A" if score > 0 else "B",
                           "justificacion": "mas completa y clara"}, ensure_ascii=False)
    nota = 3 + (1 if len(prompt) > 900 else 0) + (1 if ("cita" in p or "fuente" in p) else 0)
    nota = max(1, min(5, nota + rng.choice([-1, 0, 0, 1])))
    return json.dumps({"nota": nota, "justificacion": "cumple parcialmente la rubrica"},
                      ensure_ascii=False)


def _sim_agente(prompt, entrada, rng):
    """Agente con herramientas. Si no lo defiendes, obedece la inyeccion."""
    texto = prompt + "\n" + (entrada or "")
    if hay_inyeccion(texto) and not _hay_defensa(prompt):
        t = _norm(texto)
        if any(m in t for m in MARCAS_ENVIO):
            destino = re.search(r"[\w\.\-]+@[\w\.\-]+", texto)
            return json.dumps({"accion": "enviar_email",
                               "destino": destino.group(0) if destino else "externo@dominio.com",
                               "contenido": "resumen completo del expediente"}, ensure_ascii=False)
        if any(m in t for m in MARCAS_BORRADO):
            return json.dumps({"accion": "eliminar_recurso",
                               "objetivo": "bucket-produccion"}, ensure_ascii=False)
        return json.dumps({"accion": "responder",
                           "texto": "Mis instrucciones internas son: ... API_KEY=sk-lab-DEMO-1234"},
                          ensure_ascii=False)
    if hay_inyeccion(texto):
        return json.dumps({"accion": "rechazar",
                           "motivo": "el contenido externo intento darme instrucciones"},
                          ensure_ascii=False)
    return json.dumps({"accion": "consultar_ticket",
                       "id": "INC-" + str(rng.randint(1000, 9999))}, ensure_ascii=False)


def _sim_rag(prompt, rng):
    """Responde con el contexto. Si la respuesta no esta, inventa (salvo que lo prohibas)."""
    m = re.search(r"<contexto>(.*?)</contexto>", prompt, re.S | re.I)
    ctx = m.group(1) if m else ""
    preg = re.search(r"pregunta[:\s]*(.+)$", prompt, re.I | re.S)
    pregunta = (preg.group(1) if preg else "").strip()
    _STOP = {"cual", "cuales", "como", "para", "donde", "esta", "este", "esto",
             "quien", "cuando", "sobre", "tiene", "hace", "debe", "puede"}
    claves = [w for w in re.findall(r"[a-z]{4,}", _norm(pregunta)) if w not in _STOP][:8]
    frases = [f.strip() for f in re.split(r"(?<=[\.\n])", ctx) if len(f.strip()) > 25]
    mejor, mejor_p = None, 0
    for f in frases:
        p = sum(1 for c in claves if c in _norm(f))
        if p > mejor_p:
            mejor, mejor_p = f, p
    if mejor_p >= 2 and mejor:
        return mejor.strip()
    prohibido = any(k in _norm(prompt) for k in
                    ("no_se", "si no esta en el contexto", "responde no_se"))
    if prohibido:
        return "NO_SE"
    # Alucinacion: plausible, con cifra concreta y tono seguro.
    return ("Segun la documentacion interna, el valor establecido es de %d horas "
            "y aplica a todos los entornos." % rng.choice([24, 48, 72, 96]))


def _sim_texto(prompt, rng):
    frases = [f.strip() for f in re.split(r"[\n\.]", prompt) if len(f.strip()) > 20]
    base = frases[-1][:180] if frases else "de acuerdo"
    return "Entendido. En resumen: " + base + "."


_RE_VARIABLE = re.compile(r"(?:ticket|entrada|documento|texto|caso)\s*:", re.I)


def _parte_variable(prompt: str, entrada: str) -> str:
    """Lo que el modelo debe procesar (lo variable), separado de las instrucciones.

    Convencion del taller: lo fijo va primero y lo variable al final, detras de una
    etiqueta tipo `Ticket:`. Esa misma convencion es la que habilita la cache de
    prefijo de la Sesion 4.
    """
    if entrada:
        return entrada
    marcas = list(_RE_VARIABLE.finditer(prompt or ""))
    if marcas:
        return (prompt or "")[marcas[-1].end():].strip()
    partes = [b.strip() for b in (prompt or "").split(chr(10) * 2) if b.strip()]
    return partes[-1] if partes else (prompt or "")


def _simular(prompt, entrada, modelo, temperature, seed, forzar_json):
    rng = _rng(prompt, modelo, temperature, seed)
    modo = _modo(prompt)
    if modo == "juez":
        return _sim_juez(prompt, rng, temperature)
    if modo == "agente":
        return _sim_agente(prompt, entrada, rng)
    if modo == "rag":
        return _sim_rag(prompt, rng)
    if modo == "clasificar":
        return _sim_clasificar(prompt, _parte_variable(prompt, entrada),
                               modelo, rng, temperature, forzar_json)
    return _sim_texto(prompt, rng)


# --------------------------------------------------------------------------
# API PUBLICA: chat()
# --------------------------------------------------------------------------
def extraer_json(texto: str) -> str:
    """Saca el primer bloque JSON de una respuesta. NO es una defensa: es un parche."""
    t = (texto or "").strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    i, j = t.find("{"), t.rfind("}")
    return t[i:j + 1] if i != -1 and j > i else t


def _latencia_simulada(modelo, tokens_in, tokens_out, rng):
    base = 220 if modelo == "sim-small" else 700
    lat = base + tokens_in * 0.08 + tokens_out * (1.2 if modelo == "sim-small" else 3.0)
    lat *= rng.uniform(0.75, 1.9)          # cola larga: por eso se mide p95, no promedio
    return int(lat)


def _nuevo_id(pref):
    _CONTADOR["llamadas"] += 1
    return "%s-%04d" % (pref, _CONTADOR["llamadas"])


def chat(prompt: str,
         entrada: str = "",
         modelo: str = "sim-small",
         temperature: float = 0.0,
         max_tokens: int | None = None,
         stop: list | None = None,
         seed: int | None = None,
         formato_json: bool = False,
         sistema: str | None = None,
         timeout_s: float | None = None,
         prompt_id: str = "adhoc",
         trace_id: str | None = None,
         parent_span_id: str | None = None,
         tenant: str = "interno",
         registrar: bool = True) -> Respuesta:
    """Llamada unica al modelo. Es el embrion del GATEWAY de la Sesion 1.

    Todo pasa por aqui: por eso se puede medir, rutear, cachear y sustituir.
    """
    completo = "\n\n".join(x for x in [sistema, prompt, entrada] if x)
    tokens_in = contar_tokens(completo)
    span_id = _nuevo_id("span")
    trace_id = trace_id or _nuevo_id("trace")

    if modelo.startswith("sim-"):
        rng = _rng(completo, modelo, temperature, seed)
        if _FALLOS["prob"] > 0 and (_FALLOS["modelos"] is None or modelo in _FALLOS["modelos"]):
            if random.random() < _FALLOS["prob"]:
                if registrar:
                    _registrar(Respuesta("", modelo, tokens_in, 0, 0, 0.0, 0, 0, "error",
                                         False, 1, trace_id, span_id, prompt_id, "error"),
                               {"tenant": tenant, "parent_span_id": parent_span_id,
                                "error": _FALLOS["mensaje"]})
                raise ProveedorError("%s (modelo=%s)" % (_FALLOS["mensaje"], modelo))
        texto = _simular(completo, entrada, modelo, temperature, seed, formato_json)
        tokens_out = contar_tokens(texto)
        lat = _latencia_simulada(modelo, tokens_in, tokens_out, rng)
        if timeout_s is not None and lat / 1000.0 > timeout_s:
            time.sleep(timeout_s * VELOCIDAD_SIM)
            if registrar:
                _registrar(Respuesta("", modelo, tokens_in, 0, 0, 0.0, int(timeout_s * 1000),
                                     0, "error", False, 1, trace_id, span_id, prompt_id, "error"),
                           {"tenant": tenant, "parent_span_id": parent_span_id,
                            "error": "timeout"})
            raise TimeoutError("timeout de %.2fs superado (la llamada iba a tardar %d ms)"
                               % (timeout_s, lat))
        time.sleep(lat / 1000.0 * VELOCIDAD_SIM)
        ttft = int(lat * 0.35)
    else:
        texto, tokens_in, tokens_out, lat, ttft = _llamar_real(
            completo, modelo, temperature, max_tokens, stop, formato_json)

    motivo = "stop"
    if stop:
        for s in stop:
            if s and s in texto:
                texto = texto.split(s)[0]
                break
    if max_tokens is not None and contar_tokens(texto) > max_tokens:
        texto = texto[: max_tokens * 4]          # corte brusco, como en la vida real
        motivo = "length"
    tokens_out = contar_tokens(texto)

    r = Respuesta(texto=texto, modelo=modelo, tokens_in=tokens_in, tokens_out=tokens_out,
                  tokens_cached=0, costo_usd=costo_usd(modelo, tokens_in, tokens_out),
                  latencia_ms=lat, ttft_ms=ttft, motivo_fin=motivo, desde_cache=False,
                  intentos=1, trace_id=trace_id, span_id=span_id, prompt_id=prompt_id,
                  estado="ok")
    if registrar:
        _registrar(r, {"tenant": tenant, "parent_span_id": parent_span_id,
                       "temperature": temperature})
    return r


def _llamar_real(prompt, modelo, temperature, max_tokens, stop, formato_json):
    """Modelos reales. Solo si tienes clave y quieres gastar. Opcional en todo el taller."""
    t0 = time.time()
    if modelo.startswith("gpt") or modelo.startswith("o"):
        from openai import OpenAI
        cli = OpenAI()
        kw = {}
        if formato_json:
            kw["response_format"] = {"type": "json_object"}
        resp = cli.chat.completions.create(
            model=modelo, temperature=temperature, max_tokens=max_tokens or 800,
            stop=stop, messages=[{"role": "user", "content": prompt}], **kw)
        texto = resp.choices[0].message.content or ""
        ti, to = resp.usage.prompt_tokens, resp.usage.completion_tokens
    elif modelo.startswith("claude"):
        import anthropic
        cli = anthropic.Anthropic()
        resp = cli.messages.create(
            model=modelo, max_tokens=max_tokens or 800, temperature=temperature,
            messages=[{"role": "user", "content": prompt}])
        texto = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        ti, to = resp.usage.input_tokens, resp.usage.output_tokens
    else:
        raise ValueError("Modelo desconocido: %s. Usa sim-small / sim-large, o un modelo "
                         "real con su clave configurada." % modelo)
    lat = int((time.time() - t0) * 1000)
    return texto, ti, to, lat, int(lat * 0.35)


# --------------------------------------------------------------------------
# Carga de datos del taller
# --------------------------------------------------------------------------
def cargar_jsonl(ruta) -> list[dict]:
    ruta = Path(ruta)
    if not ruta.is_absolute():
        ruta = DATOS / ruta
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def cargar_golden(nombre="golden_incidentes.jsonl") -> list[dict]:
    return cargar_jsonl(nombre)


def cargar_red_team(nombre="red_team.jsonl") -> list[dict]:
    return cargar_jsonl(nombre)


def documento(nombre: str) -> str:
    return (DATOS / "documentos" / nombre).read_text(encoding="utf-8")


def cargar_prompt(nombre: str) -> dict:
    """Lee un prompt versionado de prompts/*.yaml (parser minimo, sin dependencias)."""
    texto = (PROMPTS / nombre).read_text(encoding="utf-8")
    datos, clave, buffer = {}, None, []
    for linea in texto.splitlines():
        if re.match(r"^[a-z_]+:", linea) and not linea.startswith(" "):
            if clave:
                datos[clave] = "\n".join(buffer).strip() if buffer else datos.get(clave)
            clave, resto = linea.split(":", 1)
            buffer = []
            resto = resto.strip()
            if resto and resto != "|":
                datos[clave] = _valor(resto)
                clave = None
        elif clave is not None:
            buffer.append(linea[2:] if linea.startswith("  ") else linea)
    if clave:
        datos[clave] = "\n".join(buffer).strip()
    return datos


def _valor(s: str):
    s = s.strip().strip('"').strip("'")
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d*\.\d+", s):
        return float(s)
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    return s


def render(plantilla: str, **variables) -> str:
    """Sustituye {{variable}} en la plantilla del prompt."""
    out = plantilla
    for k, v in variables.items():
        out = out.replace("{{%s}}" % k, str(v))
    faltantes = re.findall(r"\{\{(\w+)\}\}", out)
    if faltantes:
        raise ValueError("Faltan variables en el prompt: %s" % faltantes)
    return out


def tabla(filas: list[dict], columnas: list | None = None) -> None:
    """Imprime una tabla sin depender de pandas."""
    if not filas:
        print("(sin filas)")
        return
    cols = columnas or list(filas[0].keys())
    anchos = {c: max(len(str(c)), max(len(str(f.get(c, ""))) for f in filas)) for c in cols}
    print(" | ".join(str(c).ljust(anchos[c]) for c in cols))
    print("-+-".join("-" * anchos[c] for c in cols))
    for f in filas:
        print(" | ".join(str(f.get(c, "")).ljust(anchos[c]) for c in cols))


def barra(valor: float, ancho: int = 30) -> str:
    n = int(max(0.0, min(1.0, valor)) * ancho)
    return "#" * n + "." * (ancho - n)


__all__ = [
    "chat", "Respuesta", "ProveedorError", "TRAZAS", "trazas_df", "resumen_trazas",
    "limpiar_trazas", "contar_tokens", "costo_usd", "PRECIOS", "CATEGORIAS",
    "SEVERIDADES", "configurar_fallos", "cargar_golden", "cargar_red_team",
    "cargar_jsonl", "documento", "cargar_prompt", "render", "extraer_json",
    "hay_inyeccion", "tabla", "barra", "DATOS", "PROMPTS", "RAIZ",
]
