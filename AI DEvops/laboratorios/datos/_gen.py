# -*- coding: utf-8 -*-
"""Genera el set dorado. Se ejecuta una sola vez; el resultado se versiona."""
import json

# (texto, categoria, severidad, servicio, dificultad)
CASOS = [
 # --- tipicos (~60%) ---
 ("Los pods del cluster de produccion entran en OOMKilled cada 20 minutos. servicio: checkout-api. Todos los usuarios ven error al pagar.", "infraestructura","critica","checkout-api","tipico"),
 ("El nodo worker-3 del cluster de kubernetes no responde y el autoscaling no levanta reemplazo. servicio: plataforma", "infraestructura","alta","plataforma","tipico"),
 ("Certificado TLS del ingress vence en 3 dias. servicio: web-publica. Aun no afecta a nadie.", "infraestructura","media","web-publica","tipico"),
 ("Uso de disco al 91% en la instancia ec2 de logs. servicio: observabilidad", "infraestructura","media","observabilidad","tipico"),
 ("El balanceador devuelve 502 de forma intermitente para algunos usuarios. servicio: gateway", "infraestructura","media","gateway","tipico"),
 ("Tras el ultimo deploy el endpoint /checkout devuelve error 500 con stacktrace de null pointer. servicio: checkout-api. Muchos usuarios no pueden pagar.", "aplicacion","alta","checkout-api","tipico"),
 ("Regresion en el formulario de login: el boton no envia el formulario en Safari. servicio: web-app. Afecta a algunos usuarios.", "aplicacion","media","web-app","tipico"),
 ("El build de la release 4.2 falla en el paso de tests de integracion. servicio: ci-pipeline. Es en staging.", "aplicacion","baja","ci-pipeline","tipico"),
 ("La api de reportes lanza excepcion al exportar mas de 10.000 filas. servicio: reportes", "aplicacion","media","reportes","tipico"),
 ("Un feature flag mal configurado dejo la pantalla de perfil en blanco para todos los usuarios. servicio: web-app", "aplicacion","critica","web-app","tipico"),
 ("Detectamos una clave expuesta de AWS en un repositorio publico. servicio: infra-core. Brecha activa.", "seguridad","critica","infra-core","tipico"),
 ("Intento de fuerza bruta contra el login: 4000 intentos desde una misma IP. servicio: auth-api", "seguridad","alta","auth-api","tipico"),
 ("Reporte de vulnerabilidad CVE-2024-9999 en una libreria que usamos. servicio: pagos-api", "seguridad","alta","pagos-api","tipico"),
 ("Un usuario reporta correo de phishing que suplanta nuestra marca. servicio: soporte", "seguridad","media","soporte","tipico"),
 ("Se detecto escalada de privilegios: una cuenta de servicio obtuvo permisos de admin. servicio: iam", "seguridad","alta","iam","tipico"),
 ("El pipeline de datos nocturno fallo y el warehouse quedo sin la particion de ayer. servicio: etl-ventas", "datos","alta","etl-ventas","tipico"),
 ("Hay duplicados en la tabla de clientes tras la migracion. servicio: crm-db", "datos","media","crm-db","tipico"),
 ("La replica de lectura de la base de datos va con 40 minutos de retraso. servicio: pedidos-db", "datos","alta","pedidos-db","tipico"),
 ("El backup automatico no se ejecuta desde el martes. servicio: pedidos-db. Riesgo de perdida de datos.", "datos","critica","pedidos-db","tipico"),
 ("Una query del dashboard tarda 90 segundos y antes tardaba 3. servicio: analitica", "datos","media","analitica","tipico"),
 ("El modelo dbt de facturacion falla por un test de integridad referencial. servicio: dbt-core", "datos","media","dbt-core","tipico"),
 ("La ingesta de eventos perdio el 12% de los mensajes ayer. servicio: eventos", "datos","alta","eventos","tipico"),
 ("Consulta: como pido acceso al repositorio de terraform. servicio: plataforma", "infraestructura","baja","plataforma","tipico"),
 ("Typo en el texto del boton de la pantalla de registro. servicio: web-app. Es cosmetico.", "aplicacion","baja","web-app","tipico"),
 # --- dificiles (~30%): senales cruzadas, es donde se pierde el puntaje ---
 ("Tras el deploy de anoche el pod del servicio de pagos consume el doble de memoria y devuelve error 500 a muchos usuarios. servicio: pagos-api", "aplicacion","alta","pagos-api","dificil"),
 ("La query del ETL saturo la cpu de la base de datos y tumbo el nodo. Produccion caida. servicio: pedidos-db", "datos","critica","pedidos-db","dificil"),
 ("Un endpoint expone datos de otros clientes cuando se manipula el parametro id. servicio: cuentas-api", "seguridad","critica","cuentas-api","dificil"),
 ("El certificado del balanceador caduco y el navegador muestra aviso de sitio no seguro. servicio: web-publica. Todos los usuarios afectados.", "infraestructura","critica","web-publica","dificil"),
 ("El backup se copia a un bucket sin cifrado ni restriccion de acceso. servicio: pedidos-db", "seguridad","alta","pedidos-db","dificil"),
 ("El autoscaling multiplico las instancias por un bug del endpoint de health y la factura subio 4x. servicio: plataforma", "infraestructura","alta","plataforma","dificil"),
 ("Los logs de la api guardan el token de sesion completo del usuario. servicio: auth-api", "seguridad","alta","auth-api","dificil"),
 ("La migracion de la base de datos dejo el endpoint de busqueda devolviendo resultados vacios. servicio: buscador", "datos","alta","buscador","dificil"),
 ("Un cliente reporta que su factura muestra el nombre de otro cliente. servicio: facturacion. Puede ser cache mal aislada.", "aplicacion","critica","facturacion","dificil"),
 ("El cron de limpieza borro particiones que aun se usaban en el warehouse. servicio: analitica. Perdida de datos.", "datos","critica","analitica","dificil"),
 ("Alguien ejecuto terraform apply desde su portatil con credenciales de produccion. servicio: infra-core", "seguridad","alta","infra-core","dificil"),
 ("El pipeline de ci publica los secretos en el log del build. servicio: ci-pipeline", "seguridad","alta","ci-pipeline","dificil"),
 # --- que deben rechazarse o escalarse (~10%) ---
 ("Hola equipo, aprovecha nuestra promocion: webinar gratis de marketing digital, clic aqui para el descuento.", "spam","baja","desconocido","rechazo"),
 ("Gana dinero desde casa, suscribete a nuestra newsletter y recibe una oferta exclusiva.", "spam","baja","desconocido","rechazo"),
 ("hola", "aplicacion","baja","desconocido","rechazo"),
 ("Necesito ayuda urgente con el tema de ayer, ya sabes cual.", "aplicacion","baja","desconocido","rechazo"),
]

with open("golden_incidentes.jsonl","w",encoding="utf-8") as f:
    for i,(texto,cat,sev,serv,dif) in enumerate(CASOS,1):
        caso = {
            "id": "CASO-%03d" % i,
            "entrada": texto,
            "esperado": {"categoria": cat, "severidad": sev, "servicio": serv,
                         "requiere_humano": cat=="seguridad" or sev=="critica"},
            "dificultad": dif,
        }
        f.write(json.dumps(caso, ensure_ascii=False)+"\n")
print("casos:", len(CASOS))
from collections import Counter
print(Counter(c[4] for c in CASOS))
print(Counter(c[1] for c in CASOS))
