# -*- coding: utf-8 -*-
"""
ci_eval.py - El comando que corre en CI. Devuelve exit code 1 si el gate no pasa.

    python ci_eval.py                       # usa gate.yaml
    python ci_eval.py --prompt clasificar_incidente.v3_roto.yaml

La diferencia entre un equipo que controla su sistema y uno que lo padece cabe en
una linea: si el gate BLOQUEA o solo comenta. Aqui bloquea (sys.exit(1)).
"""
import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import lab_utils as L
from evaluador import correr_eval, guardar, comparar

BASE = RAIZ / "resultados" / "baseline.json"


def leer_gate(ruta=None):
    """Lector minimo del gate.yaml (sin dependencias)."""
    texto = (ruta or RAIZ / "gate.yaml").read_text(encoding="utf-8")
    cfg = {}
    pila = [(-1, cfg)]
    for linea in texto.splitlines():
        if not linea.strip() or linea.strip().startswith("#"):
            continue
        sangria = len(linea) - len(linea.lstrip())
        clave, _, valor = linea.strip().partition(":")
        while pila and pila[-1][0] >= sangria:
            pila.pop()
        padre = pila[-1][1]
        valor = valor.strip()
        if valor:
            if re.fullmatch(r"-?\d+", valor):
                valor = int(valor)
            elif re.fullmatch(r"-?\d*\.\d+", valor):
                valor = float(valor)
            padre[clave] = valor
        else:
            padre[clave] = {}
            pila.append((sangria, padre[clave]))
    return cfg["eval_gate"]


def evaluar_gate(resultado, cfg, anterior=None):
    """Devuelve (pasa, [motivos]). Cada motivo es una linea del informe de CI."""
    t = cfg["thresholds"]
    motivos = []
    if resultado["score_global"] < t["score_global"]:
        motivos.append("score_global %.4f < %.2f" % (resultado["score_global"], t["score_global"]))
    if resultado["validez_esquema"] < t["validez_esquema"]:
        motivos.append("validez_esquema %.4f < %.2f" % (resultado["validez_esquema"], t["validez_esquema"]))
    if resultado["costo_por_caso_usd"] > t["costo_por_caso_usd"]:
        motivos.append("costo_por_caso %.6f > %.6f" % (resultado["costo_por_caso_usd"], t["costo_por_caso_usd"]))
    if resultado["latencia_p95_ms"] > t["latencia_p95_ms"]:
        motivos.append("latencia_p95 %d ms > %d ms" % (resultado["latencia_p95_ms"], t["latencia_p95_ms"]))
    if anterior:
        estado, caidas = comparar(anterior, resultado, t["caida_por_grupo"])
        motivos.extend(caidas)
    return (len(motivos) == 0), motivos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--runs", type=int, default=None)
    ap.add_argument("--guardar-baseline", action="store_true")
    args = ap.parse_args()

    cfg = leer_gate()
    resultado = correr_eval(args.prompt or cfg["prompt"],
                            runs_por_caso=args.runs or cfg["runs_per_case"],
                            etiqueta="ci")
    anterior = json.loads(BASE.read_text(encoding="utf-8")) if BASE.exists() else None
    pasa, motivos = evaluar_gate(resultado, cfg, anterior)

    print("=" * 62)
    print("EVAL GATE  |  prompt=%s  modelo=%s  commit=%s"
          % (resultado["prompt_id"], resultado["modelo"], resultado["commit"]))
    print("  score_global      %.4f   (umbral %.2f)" % (resultado["score_global"], cfg["thresholds"]["score_global"]))
    print("  validez_esquema   %.4f   (umbral %.2f)" % (resultado["validez_esquema"], cfg["thresholds"]["validez_esquema"]))
    print("  costo_por_caso    %.6f (umbral %.6f)" % (resultado["costo_por_caso_usd"], cfg["thresholds"]["costo_por_caso_usd"]))
    print("  latencia_p95_ms   %-8d (umbral %d)" % (resultado["latencia_p95_ms"], cfg["thresholds"]["latencia_p95_ms"]))
    print("  por grupo:")
    for g, v in resultado["por_grupo"].items():
        delta = ""
        if anterior and g in anterior["por_grupo"]:
            delta = "  (%+0.3f)" % (v - anterior["por_grupo"][g])
        print("     %-22s %.3f%s" % (g, v, delta))
    guardar(resultado)
    if args.guardar_baseline:
        BASE.parent.mkdir(exist_ok=True, parents=True)
        BASE.write_text(json.dumps({k: v for k, v in resultado.items() if k != "pares"},
                                   indent=2, ensure_ascii=False), encoding="utf-8")
        print("\nbaseline guardado en", BASE)
    if pasa:
        print("\nGATE: PASA")
        return 0
    print("\nGATE: BLOQUEA (%s)" % cfg["on_fail"])
    for m in motivos:
        print("   - " + m)
    print("\nPara saltarlo hace falta aprobacion nominal con motivo y caducidad.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
