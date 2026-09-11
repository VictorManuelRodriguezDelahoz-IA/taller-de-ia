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
from collections import Counter, defaultdict
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


# --------------------------------------------------------------------------
# Para leer los resultados sin descifrar diccionarios (Sesion 2)
# --------------------------------------------------------------------------
_NOMBRE_DIFICULTAD = {"tipico": "típico", "dificil": "difícil", "rechazo": "rechazo"}


def _nombre_grupo(grupo):
    return grupo[4:] if grupo.startswith("cat:") else _NOMBRE_DIFICULTAD.get(grupo, grupo)


def _grupos_ordenados(res):
    dificultades = [g for g in ("tipico", "dificil", "rechazo") if g in res["por_grupo"]]
    categorias = sorted(g for g in res["por_grupo"] if g.startswith("cat:"))
    return dificultades, categorias


def boletin(res):
    """Imprime el resultado de correr_eval como un boletin de notas."""
    total = res["casos"] * res["runs_por_caso"]
    print("BOLETÍN DE NOTAS · %s" % res["etiqueta"])
    print("prompt %s · modelo %s · commit %s" % (res["prompt_id"], res["modelo"], res["commit"]))
    print("%d casos x %d corridas = %d predicciones evaluadas" % (res["casos"], res["runs_por_caso"], total))
    print("")
    for nombre, valor in (("Nota global", res["score_global"]),
                          ("Acierta la categoría", res["exactitud_categoria"]),
                          ("JSON válido", res["validez_esquema"])):
        print("  %-24s %.2f  %s" % (nombre, valor, L.barra(valor, 20)))
    print("  %-24s %.6f USD" % ("Costo por predicción", res["costo_por_caso_usd"]))
    print("  %-24s %d ms" % ("Tiempo (p95)", res["latencia_p95_ms"]))
    dificultades, categorias = _grupos_ordenados(res)
    for titulo, grupos in (("Nota por dificultad", dificultades), ("Nota por categoría", categorias)):
        print("")
        print("  " + titulo)
        for g in grupos:
            v = res["por_grupo"][g]
            print("    %-20s %.2f  %s" % (_nombre_grupo(g), v, L.barra(v, 20)))


def donde_se_equivoca(res, top=5):
    """Las confusiones de categoria mas frecuentes, en palabras."""
    errores = Counter((real, dijo) for real, dijo in res["pares"] if real != dijo)
    total = len(res["pares"])
    if not errores:
        print("No se equivocó de categoría ni una vez en %d predicciones." % total)
        return
    print("Se equivocó de categoría en %d de %d predicciones. Lo que más confunde:"
          % (sum(errores.values()), total))
    print("")
    for (real, dijo), veces in errores.most_common(top):
        print("  era %-16s y dijo %-18s %2d veces" % (real, dijo or "(JSON ilegible)", veces))


def comparar_versiones(antes, despues):
    """Pone dos boletines lado a lado y avisa de las categorias que bajan."""
    def fila(nombre, a, b):
        d = b - a
        marca = "sube" if d > 0.005 else ("BAJA" if d < -0.005 else "igual")
        print("  %-24s %.2f  ->  %.2f   %+.2f  %s" % (nombre, a, b, d, marca))

    print("%s  ->  %s" % (antes["etiqueta"], despues["etiqueta"]))
    print("")
    fila("Nota global", antes["score_global"], despues["score_global"])
    fila("Acierta la categoría", antes["exactitud_categoria"], despues["exactitud_categoria"])
    fila("JSON válido", antes["validez_esquema"], despues["validez_esquema"])
    dificultades, categorias = _grupos_ordenados(despues)
    bajan = []
    for titulo, grupos in (("Por dificultad", dificultades), ("Por categoría", categorias)):
        print("")
        print("  " + titulo)
        for g in grupos:
            a, b = antes["por_grupo"].get(g, 0.0), despues["por_grupo"][g]
            fila("  " + _nombre_grupo(g), a, b)
            if g.startswith("cat:") and b - a < -0.005:
                bajan.append(_nombre_grupo(g))
    print("")
    if bajan and despues["score_global"] > antes["score_global"]:
        print("  OJO: la nota global sube, pero baja: %s." % ", ".join(bajan))
    elif bajan:
        print("  Baja la nota global y también: %s." % ", ".join(bajan))
    else:
        print("  Ninguna categoría baja.")
