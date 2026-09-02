# -*- coding: utf-8 -*-
"""Convierte un archivo .py en formato porcentual a un notebook .ipynb.

    python _fuente/mknb.py _fuente/sesion1.py notebooks/Sesion_1_....ipynb

Formato:
    # %% [markdown]
    # texto markdown
    # %%
    codigo
"""
import hashlib
import io
import json
import sys


def _id(n):
    """Identificador estable por posicion: nbformat lo exige a partir de la 4.5."""
    return "celda-%03d" % n


def construir(ruta_py, ruta_nb):
    lineas = io.open(ruta_py, encoding="utf-8").read().splitlines()
    celdas, tipo, buf = [], None, []

    def cerrar():
        if tipo is None:
            return
        txt = "\n".join(buf).strip("\n")
        if not txt.strip():
            return
        if tipo == "markdown":
            fuente = "\n".join(l[2:] if l.startswith("# ") else ("" if l.strip() == "#" else l)
                               for l in txt.splitlines())
            celdas.append({"cell_type": "markdown", "metadata": {}, "id": _id(len(celdas)),
                           "source": fuente.splitlines(keepends=True)})
        else:
            celdas.append({"cell_type": "code", "execution_count": None, "metadata": {},
                           "id": _id(len(celdas)), "outputs": [],
                           "source": txt.splitlines(keepends=True)})

    for l in lineas:
        if l.startswith("# %% [markdown]"):
            cerrar(); tipo, buf = "markdown", []
        elif l.startswith("# %%"):
            cerrar(); tipo, buf = "code", []
        else:
            buf.append(l)
    cerrar()

    nb = {"cells": celdas,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                      "name": "python3"},
                       "language_info": {"name": "python", "version": "3.11"}},
          "nbformat": 4, "nbformat_minor": 5}
    io.open(ruta_nb, "w", encoding="utf-8", newline="\n").write(
        json.dumps(nb, ensure_ascii=False, indent=1))
    print("%s -> %s (%d celdas)" % (ruta_py, ruta_nb, len(celdas)))


if __name__ == "__main__":
    construir(sys.argv[1], sys.argv[2])
