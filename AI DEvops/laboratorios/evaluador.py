# -*- coding: utf-8 -*-
"""
evaluador.py - El runner de evaluacion que se construye en la Sesion 2.

Se deja aqui ya resuelto para que las Sesiones 3, 4 y 5 puedan importarlo:

    from evaluador import correr_eval, comparar, guardar

Es exactamente el mismo codigo del notebook de la Sesion 2.
"""
from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from pathlib import Path

import lab_utils as L
from lab_utils import chat

RAIZ = Path(__file__).resolve().parent
RESULTADOS = RAIZ / "resultados"
CAMPOS = ("categoria", "severidad", "servicio", "requiere_humano")


def valido(d) -> bool:
    return (isinstance(d, dict)
            and d.get("categoria") in L.CATEGORIAS
            and d.get("severidad") in L.SEVERIDADES
            and isinstance(d.get("servicio"), str)
            and isinstance(d.get("requiere_humano"), bool))


def coincidencia_campos(obtenido, esperado) -> float:
    if not isinstance(obtenido, dict):
        return 0.0
    return sum(obtenido.get(c) == esperado[c] for c in CAMPOS) / len(CAMPOS)


def hash_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=str(RAIZ), stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "sin-git"


def correr_eval(archivo_prompt, casos=None, runs_por_caso=3, modelo=None, etiqueta="",
                gateway=None):
    """Corre el set dorado y devuelve un resultado comparable y guardable.

    `gateway`: funcion opcional (ticket, prompt_dict) -> (dict_salida, costo_usd).
    Sirve para evaluar la version con cache, ruteo o fallback de la Sesion 4.
    """
    casos = casos if casos is not None else L.cargar_golden()
    p = L.cargar_prompt(archivo_prompt)
    modelo = modelo or p["modelo"]
    prompt_id = "%s:%s" % (p["id"], p["version"])
    L.limpiar_trazas()

    pares, campos, validos, detalle = [], [], 0, defaultdict(list)
    costo_manual = 0.0
    for c in casos:
        for _ in range(runs_por_caso):
            if gateway is not None:
                d, costo = gateway(c["entrada"], p)
                costo_manual += costo
            else:
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
    costo = tr.get("costo_total_usd", 0.0) or costo_manual
    return {
        "etiqueta": etiqueta or archivo_prompt,
        "prompt_id": prompt_id,
        "modelo": modelo,
        "commit": hash_commit(),
        "casos": len(casos),
        "runs_por_caso": runs_por_caso,
        "score_global": round(sum(campos) / n, 4),
        "exactitud_categoria": round(sum(1 for r, pr in pares if r == pr) / n, 4),
        "validez_esquema": round(validos / n, 4),
        "por_grupo": {k: round(sum(v) / len(v), 4) for k, v in sorted(detalle.items())},
        "costo_usd": round(costo, 6),
        "costo_por_caso_usd": round(costo / n, 6),
        "latencia_p95_ms": tr.get("latencia_p95_ms", 0),
        "pares": pares,
    }


def guardar(resultado, destino=None) -> Path:
    destino = Path(destino or RESULTADOS)
    destino.mkdir(exist_ok=True, parents=True)
    nombre = "eval_%s_%s.json" % (resultado["prompt_id"].replace(":", "_"), resultado["commit"])
    ruta = destino / nombre
    ruta.write_text(json.dumps({k: v for k, v in resultado.items() if k != "pares"},
                               indent=2, ensure_ascii=False), encoding="utf-8")
    return ruta


def comparar(anterior, nuevo, caida_maxima=0.05):
    """Un global que sube puede esconder una clase rota. Esto lo impide."""
    motivos = []
    for grupo, valor in nuevo["por_grupo"].items():
        antes = anterior["por_grupo"].get(grupo)
        if antes is None:
            continue
        if antes - valor > caida_maxima:
            motivos.append("%s cae %.3f (%.3f -> %.3f)" % (grupo, antes - valor, antes, valor))
    return ("BLOQUEAR" if motivos else "PASA"), motivos
