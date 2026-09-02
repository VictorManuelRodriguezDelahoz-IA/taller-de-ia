# -*- coding: utf-8 -*-
"""Comprobacion de 10 segundos antes de empezar el taller.

    python verificar_entorno.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

fallos = []
print("Python:", sys.version.split()[0])
if sys.version_info < (3, 9):
    fallos.append("Hace falta Python 3.9 o superior.")

try:
    import lab_utils as L
    print("lab_utils: ok")
except Exception as e:                                    # pragma: no cover
    fallos.append("no se pudo importar lab_utils: %s" % e)
    L = None

if L:
    for nombre, ruta in (("set dorado", L.DATOS / "golden_incidentes.jsonl"),
                         ("set de seguridad", L.DATOS / "red_team.jsonl"),
                         ("documentos", L.DATOS / "documentos"),
                         ("prompts", L.PROMPTS)):
        print("%-18s %s" % (nombre + ":", "ok" if ruta.exists() else "FALTA " + str(ruta)))
        if not ruta.exists():
            fallos.append("falta " + str(ruta))

    try:
        r = L.chat("Clasifica el ticket. Categorias: infraestructura, aplicacion, "
                   "seguridad, datos, spam. Responde SOLO JSON.\n\n"
                   "Ticket: el nodo del cluster no responde. servicio: plataforma",
                   modelo="sim-small", formato_json=True, registrar=False)
        print("llamada simulada: ok ->", r.texto[:70])
        print("  tokens_in=%d tokens_out=%d costo=%.8f USD latencia=%d ms"
              % (r.tokens_in, r.tokens_out, r.costo_usd, r.latencia_ms))
    except Exception as e:
        fallos.append("la llamada simulada fallo: %s" % e)

for extra in ("pandas", "tiktoken", "openai", "anthropic"):
    try:
        __import__(extra)
        print("%-18s ok (opcional)" % (extra + ":"))
    except ImportError:
        print("%-18s no instalado (opcional, no hace falta)" % (extra + ":"))

print()
if fallos:
    print("HAY PROBLEMAS:")
    for f in fallos:
        print("  -", f)
    sys.exit(1)
print("Todo listo. Abre notebooks/Sesion_1_Fundamentos_y_Arquitectura.ipynb")
