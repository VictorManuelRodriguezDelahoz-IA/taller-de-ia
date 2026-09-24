# -*- coding: utf-8 -*-
"""
aiops.py - Entorno de produccion simulado y visualizaciones para el laboratorio
"IA aplicada a DevOps: un agente de respuesta a incidentes".

Genera tres horas de telemetria (metricas, despliegues, cambios de configuracion y
logs) de cinco servicios, con un incidente dentro. No necesita librerias externas:
los graficos son SVG generados en Python, para que el laboratorio funcione con el
mismo requirements.txt del taller.
"""
from __future__ import annotations

import copy
import html
import random
import re

INICIO_HORA = 1          # el minuto 0 son las 01:00
MINUTOS = 180            # tres horas de telemetria
NL = chr(10)

SERVICIOS = ["web-app", "checkout-api", "pagos-api", "auth-api", "pedidos-db"]

# Quien llama a quien: el de la izquierda depende de los de la derecha.
DEPENDENCIAS = {
    "web-app": ["checkout-api", "auth-api"],
    "checkout-api": ["pagos-api", "pedidos-db"],
    "pagos-api": [],
    "auth-api": [],
    "pedidos-db": [],
}

BASE = {
    "web-app":      {"errores": 0.30, "p95": 180, "cpu": 40, "rps": 120},
    "checkout-api": {"errores": 0.20, "p95": 220, "cpu": 35, "rps": 40},
    "pagos-api":    {"errores": 0.20, "p95": 150, "cpu": 30, "rps": 35},
    "auth-api":     {"errores": 0.10, "p95": 90,  "cpu": 25, "rps": 80},
    "pedidos-db":   {"errores": 0.05, "p95": 12,  "cpu": 35, "rps": 300},
}

SLOS = {"checkout-api": 99.5, "web-app": 99.5}      # disponibilidad objetivo, en %

ESCENARIOS = ("deploy_defectuoso", "certificado_expirado")

_RUIDO = {
    "web-app": ["INFO GET /home 200 in %dms", "WARN slow render path=/catalogo took %dms"],
    "checkout-api": ["INFO POST /checkout 200 in %dms", "WARN retrying call to pagos-api after %dms"],
    "pagos-api": ["INFO charge authorized in %dms", "WARN card network latency %dms"],
    "auth-api": ["INFO token issued in %dms", "INFO session refreshed in %dms"],
    "pedidos-db": ["INFO checkpoint complete in %dms", "WARN slow query took %dms table=pedidos"],
}


def hora(minuto):
    """Minuto del escenario -> 'HH:MM'."""
    minuto = int(round(minuto))
    return "%02d:%02d" % (INICIO_HORA + minuto // 60, minuto % 60)


def _log(esc, minuto, servicio, mensaje, incidente=False):
    esc["logs"].append({"minuto": minuto, "servicio": servicio, "mensaje": mensaje,
                        "incidente": incidente})


def crear_escenario(nombre="deploy_defectuoso", semilla=7):
    """Tres horas de telemetria de produccion con un incidente dentro."""
    if nombre not in ESCENARIOS:
        raise ValueError("Escenario desconocido: %s. Opciones: %s" % (nombre, ", ".join(ESCENARIOS)))
    rng = random.Random(semilla)
    n = MINUTOS
    base = {}
    for s in SERVICIOS:
        b = BASE[s]
        base[s] = {
            "errores": [max(0.0, b["errores"] * (1 + rng.gauss(0, 0.25))) for _ in range(n)],
            "p95": [max(1.0, b["p95"] * (1 + rng.gauss(0, 0.08))) for _ in range(n)],
            "cpu": [min(100.0, max(1.0, b["cpu"] + rng.gauss(0, 2.5))) for _ in range(n)],
            "rps": [max(1.0, b["rps"] * (1 + rng.gauss(0, 0.05))) for _ in range(n)],
        }
    esc = {"nombre": nombre, "minutos": n, "metricas": copy.deepcopy(base), "_base": base,
           "despliegues": [], "cambios_config": [], "logs": [], "acciones": [],
           "inicio_real": None, "causa_real": None, "afectados": {}, "remediado_en": None}

    for m in range(n):                                   # ruido normal de produccion
        for s, plantillas in _RUIDO.items():
            if rng.random() < 0.3:
                _log(esc, m, s, rng.choice(plantillas) % rng.randint(20, 900))

    # Un pico transitorio de 3 minutos que se arregla solo: sirve para ver falsos positivos.
    for m, v in ((75, 1.6), (76, 2.4), (77, 1.1)):
        esc["metricas"]["checkout-api"]["errores"][m] = v

    esc["cambios_config"].append({"minuto": 100, "servicio": "auth-api",
                                  "detalle": "rate_limit 800 -> 1000 req/s"})
    _log(esc, 100, "auth-api", "INFO rate limit updated to 1000 req/s")
    esc["despliegues"].append({"minuto": 60, "servicio": "pagos-api", "de": "1.8.2", "a": "1.8.3"})
    _log(esc, 60, "pagos-api", "INFO deployment pagos-api 1.8.3 healthy (2/2 pods ready)")

    met = esc["metricas"]
    if nombre == "deploy_defectuoso":
        esc["despliegues"].append({"minuto": 118, "servicio": "checkout-api", "de": "2.13.2", "a": "2.14.0"})
        _log(esc, 118, "checkout-api", "INFO deployment checkout-api 2.14.0 rolled out (3/3 pods ready)")
        for m in range(119, n):
            met["checkout-api"]["errores"][m] = {119: 12.0, 120: 31.0}.get(m, 40 + rng.gauss(0, 2.5))
            met["checkout-api"]["p95"][m] = {119: 1600.0}.get(m, 5000 + rng.gauss(0, 250))
            for _ in range(4):
                _log(esc, m, "checkout-api", "ERROR PoolTimeoutError: connection pool exhausted "
                     "(max=10, waited 5000ms) order_id=%d" % rng.randint(10000, 99999), True)
            if m >= 120:
                met["web-app"]["errores"][m] = 8 + rng.gauss(0, 0.8)
                met["web-app"]["p95"][m] = 950 + rng.gauss(0, 60)
                for _ in range(2):
                    _log(esc, m, "web-app", "ERROR upstream checkout-api returned 503 path=/checkout "
                         "req_id=%06x" % rng.randint(0, 16 ** 6 - 1), True)
            if m >= 121:
                met["pedidos-db"]["cpu"][m] = min(99.0, 88 + rng.gauss(0, 2.5))
                met["pedidos-db"]["p95"][m] = 60 + rng.gauss(0, 5)
                _log(esc, m, "pedidos-db", "WARN too many connections from checkout-api active=%d"
                     % rng.randint(400, 520), True)
        esc["inicio_real"] = 119
        esc["causa_real"] = {"tipo": "despliegue", "servicio": "checkout-api",
                             "accion_correcta": "rollback", "version_buena": "2.13.2"}
        esc["afectados"] = {"checkout-api": ["errores", "p95"], "web-app": ["errores", "p95"],
                            "pedidos-db": ["cpu", "p95"]}
    else:
        esc["despliegues"].insert(0, {"minuto": 20, "servicio": "checkout-api", "de": "2.13.1", "a": "2.13.2"})
        for m in range(125, n):
            met["web-app"]["errores"][m] = {125: 18.0}.get(m, 34 + rng.gauss(0, 2))
            met["web-app"]["p95"][m] = 420 + rng.gauss(0, 30)
            met["auth-api"]["rps"][m] = 45 + rng.gauss(0, 3)
            for _ in range(4):
                _log(esc, m, "web-app", "ERROR tls: x509: certificate has expired or is not yet valid "
                     "(auth-api.internal) req_id=%06x" % rng.randint(0, 16 ** 6 - 1), True)
        esc["inicio_real"] = 125
        esc["causa_real"] = {"tipo": "certificado", "servicio": "auth-api",
                             "accion_correcta": "renovar_certificado"}
        esc["afectados"] = {"web-app": ["errores", "p95"], "auth-api": ["rps"]}

    esc["logs"].sort(key=lambda l: l["minuto"])
    return esc


def aplicar_accion(esc, accion, minuto):
    """Ejecuta una accion sobre el entorno. Solo arregla el incidente si ataca la causa real."""
    nuevo = copy.deepcopy(esc)
    causa = esc["causa_real"]
    correcta = (accion.get("accion") == causa["accion_correcta"]
                and accion.get("servicio") == causa["servicio"])
    nuevo["acciones"].append({"minuto": minuto, "accion": dict(accion), "arregla": correcta})
    if correcta:
        recuperado = minuto + 2
        for servicio, metricas in esc["afectados"].items():
            for metrica in metricas:
                for m in range(recuperado, esc["minutos"]):
                    nuevo["metricas"][servicio][metrica][m] = esc["_base"][servicio][metrica][m]
        nuevo["logs"] = [l for l in esc["logs"] if not (l["incidente"] and l["minuto"] >= recuperado)]
        nuevo["remediado_en"] = recuperado
        if accion.get("accion") == "rollback":
            nuevo["despliegues"].append({"minuto": minuto, "servicio": accion["servicio"],
                                         "de": "", "a": accion.get("version_objetivo", "?"),
                                         "rollback": True})
    return nuevo, correcta


RUNBOOKS = {
    "rollback": {
        "id": "RB-01", "titulo": "Rollback de un despliegue", "reversible": True, "riesgo": "bajo",
        "pasos": ["Confirmar en el registro de despliegues la última versión estable",
                  "Fijar esa versión en la configuración del entorno",
                  "Aplicar y esperar a que todos los pods estén listos",
                  "Verificar que el burn rate vuelve por debajo de 1 durante 5 minutos"]},
    "reiniciar_pods": {
        "id": "RB-02", "titulo": "Reinicio escalonado de pods", "reversible": True, "riesgo": "bajo",
        "pasos": ["Reiniciar los pods de uno en uno", "Esperar a que cada pod esté listo",
                  "Verificar tasa de errores y latencia"]},
    "renovar_certificado": {
        "id": "RB-03", "titulo": "Renovación de certificado TLS", "reversible": False, "riesgo": "medio",
        "pasos": ["Emitir un certificado nuevo desde la CA interna", "Publicarlo en el secreto del servicio",
                  "Recargar el servicio sin cortar conexiones", "Verificar el handshake desde los clientes"]},
    "escalar_base_de_datos": {
        "id": "RB-04", "titulo": "Escalado vertical de base de datos", "reversible": False, "riesgo": "alto",
        "pasos": ["Abrir ventana de mantenimiento", "Crear snapshot",
                  "Cambiar el tamaño de la instancia (implica reinicio)", "Verificar réplicas y conexiones"]},
}


# --------------------------------------------------------------------------
# Graficos SVG (sin dependencias)
# --------------------------------------------------------------------------
COLORES = {"azul": "#2563eb", "rojo": "#dc2626", "ambar": "#d97706", "verde": "#16a34a",
           "gris": "#6b7280", "violeta": "#7c3aed", "cian": "#0891b2", "rosa": "#db2777"}
COLOR_SERVICIO = {"web-app": "#2563eb", "checkout-api": "#dc2626", "pagos-api": "#16a34a",
                  "auth-api": "#7c3aed", "pedidos-db": "#d97706"}


def _fmt(v):
    if v >= 1000:
        return "%.1fk" % (v / 1000)
    if v >= 10:
        return "%.0f" % v
    return "%.1f" % v


def grafico(series, titulo="", unidad="", alto=220, ancho=880, lineas_h=(), marcas=(), zonas=(),
            desde=0, hasta=None, y_max=None):
    """Grafico de lineas en SVG.

    series:   [(nombre, valores, color)]
    lineas_h: [(valor, etiqueta, color)]         umbrales horizontales
    marcas:   [(minuto, etiqueta, color)]        eventos verticales
    zonas:    [(desde, hasta, color, etiqueta)]  bandas sombreadas
    """
    hasta = (len(series[0][1]) - 1) if hasta is None else hasta
    ml, mr, mt, mb = 58, 18, 36, 30
    x0, x1, y0, y1 = ml, ancho - mr, alto - mb, mt
    valores = [v for _, vs, _ in series for v in vs[desde:hasta + 1]] + [v for v, _, _ in lineas_h]
    tope = y_max if y_max else (max(valores) * 1.15 if valores and max(valores) > 0 else 1.0)

    def X(m):
        return x0 + (m - desde) * (x1 - x0) / max(1, hasta - desde)

    def Y(v):
        return y0 - min(max(v, 0), tope) * (y0 - y1) / tope

    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
         'style="font-family:Segoe UI,Helvetica,Arial,sans-serif;max-width:100%%;display:block;margin:6px 0">'
         % (ancho, alto, ancho, alto),
         '<rect width="%d" height="%d" fill="#ffffff" stroke="#e5e7eb" rx="8"/>' % (ancho, alto),
         '<text x="%d" y="21" font-size="13" font-weight="700" fill="#111827">%s</text>' % (ml, html.escape(titulo))]
    for a, b, color, etiqueta in zonas:
        s.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s" fill-opacity="0.10"/>'
                 % (X(a), y1, max(1.0, X(b) - X(a)), y0 - y1, color))
        if etiqueta:
            s.append('<text x="%.1f" y="%d" font-size="10" fill="%s">%s</text>'
                     % (X(a) + 4, y0 - 6, color, html.escape(etiqueta)))
    for i in range(5):
        v = tope * i / 4
        y = Y(v)
        s.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#f1f5f9" stroke-width="1"/>' % (x0, y, x1, y))
        s.append('<text x="%d" y="%.1f" font-size="10" fill="#6b7280" text-anchor="end">%s%s</text>'
                 % (x0 - 6, y + 3, _fmt(v), unidad))
    primero = desde + (-desde) % 30
    for m in range(primero, hasta + 1, 30):
        s.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#9ca3af"/>' % (X(m), y0, X(m), y0 + 4))
        s.append('<text x="%.1f" y="%d" font-size="10" fill="#6b7280" text-anchor="middle">%s</text>'
                 % (X(m), y0 + 16, hora(m)))
    for v, etiqueta, color in lineas_h:
        y = Y(v)
        s.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1.2" stroke-dasharray="6 4"/>'
                 % (x0, y, x1, y, color))
        s.append('<text x="%d" y="%.1f" font-size="10" fill="%s" text-anchor="end">%s</text>'
                 % (x1 - 4, y - 4, color, html.escape(etiqueta)))
    for nombre, vs, color in series:
        puntos = " ".join("%.1f,%.1f" % (X(m), Y(vs[m])) for m in range(desde, hasta + 1))
        s.append('<polyline fill="none" stroke="%s" stroke-width="1.8" stroke-linejoin="round" points="%s"/>'
                 % (color, puntos))
    for i, (m, etiqueta, color) in enumerate(marcas):
        x = X(m)
        s.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="1.6" stroke-dasharray="3 3"/>'
                 % (x, y1, x, y0, color))
        s.append('<text x="%.1f" y="%d" font-size="10" font-weight="600" fill="%s">%s</text>'
                 % (x + 4, y1 + 11 + 12 * (i % 3), color, html.escape(etiqueta)))
    lx = x1
    for nombre, _, color in reversed(series):
        lx -= 7 * len(nombre) + 26
        s.append('<line x1="%d" y1="17" x2="%d" y2="17" stroke="%s" stroke-width="3"/>' % (lx, lx + 14, color))
        s.append('<text x="%d" y="21" font-size="11" fill="#374151">%s</text>' % (lx + 18, html.escape(nombre)))
    s.append("</svg>")
    return "".join(s)


_BLOQUES = "▁▂▃▄▅▆▇█"


def sparkline(valores, ancho=48):
    """Version en texto de una serie, para cuando no hay notebook."""
    if not valores:
        return ""
    paso = max(1, len(valores) // ancho)
    muestra = [max(valores[i:i + paso]) for i in range(0, len(valores), paso)]
    tope = max(muestra) or 1.0
    return "".join(_BLOQUES[min(7, int(v / tope * 7.999))] for v in muestra)


def resumen_serie(nombre, valores, unidad="", desde=0):
    pico = max(range(len(valores)), key=lambda i: valores[i])
    return "  %-26s %s  max %s%s a las %s" % (nombre, sparkline(valores), _fmt(valores[pico]), unidad,
                                               hora(desde + pico))


# --------------------------------------------------------------------------
# Salida enriquecida: HTML en el notebook, texto fuera de el
# --------------------------------------------------------------------------
_CSS = "font-family:Segoe UI,Helvetica,Arial,sans-serif;color:#111827;"


def _en_notebook():
    try:
        from IPython import get_ipython
        ip = get_ipython()
        return ip is not None and "IPKernelApp" in getattr(ip, "config", {})
    except Exception:
        return False


def _texto_plano(contenido):
    t = re.sub(r"<(br|/div|/tr|/li|/h[1-6]|/svg)[^>]*>", NL, contenido)
    t = re.sub(r"</t[dh]>", " | ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    lineas = [" ".join(l.split()) for l in t.split(NL)]
    return NL.join(l for l in lineas if l.strip(" |"))


def mostrar(contenido_html, texto=None):
    """Muestra HTML en el notebook; fuera de el, una version en texto."""
    if _en_notebook():
        from IPython.display import HTML, display
        display(HTML(contenido_html))
    else:
        print(texto if texto is not None else _texto_plano(contenido_html))


def mostrar_markdown(md):
    if _en_notebook():
        from IPython.display import Markdown, display
        display(Markdown(md))
    else:
        print(md)


def _celda(v):
    v = str(v)
    return v if v.startswith("<") else html.escape(v)


def insignia(texto, color):
    return ('<span style="display:inline-block;padding:2px 10px;border-radius:999px;background:%s;'
            'color:#ffffff;font-size:12px;font-weight:700">%s</span>' % (color, html.escape(texto)))


def tarjeta(titulo, filas=(), color="#2563eb", subtitulo="", pie=""):
    cuerpo = "".join('<tr><td style="padding:3px 16px 3px 0;color:#6b7280;white-space:nowrap;vertical-align:top">'
                     '%s</td><td style="padding:3px 0">%s</td></tr>' % (html.escape(str(k)), _celda(v))
                     for k, v in filas)
    return ('<div style="%sbackground:#ffffff;border:1px solid #e5e7eb;border-left:6px solid %s;'
            'border-radius:10px;padding:12px 16px;margin:8px 0;max-width:880px">' % (_CSS, color)
            + '<div style="font-size:15px;font-weight:700">%s</div>' % html.escape(titulo)
            + ('<div style="font-size:12px;color:#6b7280;margin-top:2px">%s</div>' % html.escape(subtitulo)
               if subtitulo else "")
            + ('<table style="margin-top:8px;font-size:13px;border-collapse:collapse">%s</table>' % cuerpo
               if filas else "")
            + ('<div style="margin-top:8px;font-size:12.5px;color:#374151">%s</div>' % pie if pie else "")
            + "</div>")


def kpis(items):
    """items: [(etiqueta, valor, nota, color)]"""
    celdas = "".join(
        '<div style="flex:1;min-width:150px;background:#ffffff;border:1px solid #e5e7eb;border-top:4px solid %s;'
        'border-radius:10px;padding:10px 14px"><div style="font-size:12px;color:#6b7280">%s</div>'
        '<div style="font-size:26px;font-weight:800;color:%s;line-height:1.2">%s</div>'
        '<div style="font-size:11px;color:#6b7280">%s</div></div>'
        % (c, html.escape(e), c, html.escape(str(v)), html.escape(n)) for e, v, n, c in items)
    return '<div style="%sdisplay:flex;gap:10px;flex-wrap:wrap;margin:8px 0;max-width:880px">%s</div>' % (_CSS, celdas)


TIPOS_PASO = {"codigo": ("#2563eb", "código"), "ia": ("#7c3aed", "IA"), "humano": ("#d97706", "persona"),
              "ok": ("#16a34a", "ok"), "bloqueado": ("#dc2626", "bloqueado"), "pendiente": ("#9ca3af", "pendiente")}


def flujo(pasos):
    """pasos: [(nombre, tipo, detalle)] con tipo en TIPOS_PASO."""
    partes = []
    for i, (nombre, tipo, detalle) in enumerate(pasos):
        color, etiqueta = TIPOS_PASO.get(tipo, ("#6b7280", tipo))
        partes.append('<div style="min-width:108px;max-width:150px;background:#ffffff;border:1.5px solid %s;'
                      'border-radius:10px;padding:8px 10px"><div style="font-size:10px;font-weight:800;color:%s;'
                      'text-transform:uppercase;letter-spacing:.05em">%s</div><div style="font-size:13px;'
                      'font-weight:700;margin-top:2px">%s</div><div style="font-size:11px;color:#6b7280;'
                      'margin-top:3px">%s</div></div>'
                      % (color, color, etiqueta, html.escape(nombre), html.escape(detalle)))
        if i < len(pasos) - 1:
            partes.append('<div style="align-self:center;color:#9ca3af;font-size:18px">&#8594;</div>')
    return ('<div style="%sdisplay:flex;gap:6px;flex-wrap:wrap;align-items:stretch;margin:8px 0;max-width:920px">'
            '%s</div>' % (_CSS, "".join(partes)))


def linea_de_tiempo(eventos):
    """eventos: [(minuto, texto, color)]"""
    filas = "".join('<div style="display:flex;gap:10px;align-items:flex-start;margin:0 0 7px 0">'
                    '<div style="font-family:Consolas,monospace;font-size:12.5px;color:#374151;min-width:44px">%s</div>'
                    '<div style="width:10px;height:10px;border-radius:50%%;background:%s;margin-top:4px;flex:none"></div>'
                    '<div style="font-size:13px">%s</div></div>' % (hora(m), c, html.escape(t))
                    for m, t, c in eventos)
    return ('<div style="%sbackground:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:12px 16px;'
            'margin:8px 0;max-width:880px">%s</div>' % (_CSS, filas))


def tabla(filas, columnas, titulo=""):
    cabecera = "".join('<th style="text-align:left;padding:6px 10px;border-bottom:2px solid #e5e7eb;'
                       'font-size:12px;color:#374151">%s</th>' % html.escape(c) for c in columnas)
    cuerpo = "".join("<tr>" + "".join('<td style="padding:5px 10px;border-bottom:1px solid #f1f5f9;'
                                      'font-size:12.5px;vertical-align:top">%s</td>' % _celda(f.get(c, ""))
                                      for c in columnas) + "</tr>" for f in filas)
    return ('<div style="%sbackground:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:10px 12px;'
            'margin:8px 0;max-width:920px;overflow-x:auto">%s<table style="border-collapse:collapse;width:100%%">'
            '<tr>%s</tr>%s</table></div>'
            % (_CSS, ('<div style="font-weight:700;margin-bottom:6px">%s</div>' % html.escape(titulo)) if titulo else "",
               cabecera, cuerpo))


def mostrar_grafico(series, texto_titulo="", unidad="", **kw):
    """Grafico SVG en el notebook; sparklines fuera de el."""
    svg = grafico(series, titulo=texto_titulo, unidad=unidad, **kw)
    desde = kw.get("desde", 0)
    hasta = kw.get("hasta")
    texto = NL.join([texto_titulo] + [resumen_serie(n, v[desde:(hasta + 1 if hasta is not None else None)], unidad, desde)
                                      for n, v, _ in series])
    mostrar(svg, texto)


def _markdown_basico(texto):
    """Negritas y saltos de linea para textos que devuelve un modelo."""
    texto = re.sub(r"^```[A-Za-z]*[ 	]*$", "", texto, flags=re.M).strip()   # bloques de codigo sobrantes
    t = html.escape(texto)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r'<code style="background:#f1f5f9;padding:0 4px;border-radius:4px">\1</code>', t)
    return t.replace(NL, "<br>")


def mensaje_chat(canal, texto, autor="agente-sre"):
    """Un mensaje con aspecto de chat (ChatOps)."""
    return ('<div style="%sbackground:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:12px 16px;'
            'margin:8px 0;max-width:780px"><div style="font-size:12px;color:#6b7280;margin-bottom:8px"># %s</div>'
            '<div style="display:flex;gap:10px"><div style="width:36px;height:36px;border-radius:8px;background:#7c3aed;'
            'color:#ffffff;font-weight:800;font-size:13px;display:flex;align-items:center;justify-content:center;'
            'flex:none">IA</div><div><div style="font-weight:700;font-size:14px">%s '
            '<span style="font-weight:400;color:#9ca3af;font-size:11px">APP</span></div>'
            '<div style="font-size:14px;line-height:1.5;margin-top:3px">%s</div></div></div></div>'
            % (_CSS, html.escape(canal.lstrip("#")), html.escape(autor), _markdown_basico(texto)))


def mostrar_codigo(texto, titulo=""):
    """Bloque monoespaciado para logs crudos o JSON."""
    cabecera = ('<div style="font-size:12px;color:#94a3b8;margin-bottom:6px">%s</div>' % html.escape(titulo)
                if titulo else "")
    contenido = ('<div style="%sbackground:#0f172a;border-radius:10px;padding:12px 14px;margin:8px 0;'
                 'max-width:920px;overflow-x:auto">%s<pre style="margin:0;color:#e2e8f0;'
                 'font-family:Consolas,Menlo,monospace;font-size:12px;line-height:1.45;white-space:pre">%s</pre></div>'
                 % (_CSS, cabecera, html.escape(texto)))
    mostrar(contenido, (titulo + NL if titulo else "") + texto)


texto_html = _markdown_basico
