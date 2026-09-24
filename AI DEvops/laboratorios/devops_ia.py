# -*- coding: utf-8 -*-
"""
devops_ia.py - Datos del laboratorio "IA para DevOps".

Aqui estan los tres casos que se trabajan en el notebook:

    LOG_CI, DIFF_CI       un pipeline de GitHub Actions que falla y el commit que lo rompio
    PLAN_TF               la salida de `terraform show -json` de un PR
    kubectl(...)          un cluster de Kubernetes simulado, solo lectura

y las respuestas guardadas que se usan cuando no hay clave de OpenRouter.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Caso 1: un pipeline que falla
# ---------------------------------------------------------------------------
DIFF_CI = """commit 8f3c2a1 (feat/imagen-liviana)
Author: Laura Gómez
    Imagen base más liviana para reducir el tiempo de despliegue

diff --git a/Dockerfile b/Dockerfile
@@ -1,4 +1,4 @@
-FROM python:3.12 AS builder
+FROM python:3.12-slim AS builder
 WORKDIR /app
 COPY requirements.txt .
 RUN pip install --no-cache-dir -r requirements.txt
"""

_PAQUETES = [("fastapi", "0.115.0", "94 kB"), ("uvicorn", "0.30.6", "62 kB"), ("pydantic", "2.9.2", "434 kB"),
             ("pydantic-core", "2.23.4", "2.1 MB"), ("starlette", "0.38.6", "71 kB"), ("anyio", "4.6.0", "89 kB"),
             ("sqlalchemy", "2.0.35", "3.2 MB"), ("redis", "5.0.8", "255 kB"), ("httpx", "0.27.2", "76 kB"),
             ("structlog", "24.4.0", "67 kB"), ("prometheus-client", "0.21.0", "54 kB"), ("tenacity", "9.0.0", "28 kB"),
             ("boto3", "1.35.24", "139 kB"), ("botocore", "1.35.24", "12.5 MB"), ("orjson", "3.10.7", "141 kB")]


def _log_ci():
    t = "2026-09-18T14:02:%02d.%07dZ "
    lineas = []

    def l(texto, s=0):
        lineas.append(t % (min(59, 11 + s), 1000000 + 37 * len(lineas)) + texto)

    l("Requested labels: ubuntu-latest")
    l("Job defined at: clickit/tienda-checkout/.github/workflows/build.yml@refs/heads/feat/imagen-liviana")
    l("Waiting for a runner to pick up this job...")
    l("##[group]Run actions/checkout@v4", 1)
    l("Syncing repository: clickit/tienda-checkout", 1)
    l("HEAD is now at 8f3c2a1", 2)
    l("##[endgroup]", 2)
    l("##[warning]Node.js 16 actions are deprecated. Please update the following actions to use Node.js 20: "
      "docker/setup-buildx-action@v2", 2)
    l("##[group]Run docker/setup-buildx-action@v2", 3)
    l("Docker info: Server Version 27.2.0, Storage Driver overlay2", 3)
    l("##[endgroup]", 4)
    l("##[group]Run docker build -t registry.clickit.dev/checkout:2.14.0 .", 4)
    l("#1 [internal] load build definition from Dockerfile", 4)
    l("#1 transferring dockerfile: 412B done", 4)
    l("#2 [internal] load metadata for docker.io/library/python:3.12-slim", 5)
    l("#2 DONE 1.1s", 6)
    l("#5 [builder 1/4] FROM docker.io/library/python:3.12-slim@sha256:ad48727987b2", 6)
    l("#5 DONE 4.8s", 11)
    l("#6 [builder 2/4] WORKDIR /app", 11)
    l("#7 [builder 3/4] COPY requirements.txt .", 11)
    l("#8 [builder 4/4] RUN pip install --no-cache-dir -r requirements.txt", 12)
    s = 12.0
    for nombre, version, peso in _PAQUETES:
        s += 0.4
        l("#8 %.3f Collecting %s==%s" % (s, nombre, version), int(s))
        l("#8 %.3f   Downloading %s-%s-py3-none-any.whl (%s)" % (s + 0.05, nombre.replace("-", "_"), version, peso), int(s))
    l("#8 18.911 Collecting psycopg2==2.9.9", 18)
    l("#8 18.952   Downloading psycopg2-2.9.9.tar.gz (384 kB)", 18)
    l("#8 19.406   Preparing metadata (setup.py): started", 19)
    l("#8 19.902   Preparing metadata (setup.py): finished with status 'error'", 19)
    l("#8 19.905   error: subprocess-exited-with-error", 19)
    l("#8 19.905   × python setup.py egg_info did not run successfully.", 19)
    l("#8 19.905   │ exit code: 1", 19)
    l("#8 19.905   ╰─> [23 lines of output]", 19)
    l("#8 19.905       running egg_info", 19)
    l("#8 19.905       creating /tmp/pip-pip-egg-info-k2x9/psycopg2.egg-info", 19)
    l("#8 19.905       writing /tmp/pip-pip-egg-info-k2x9/psycopg2.egg-info/PKG-INFO", 19)
    l("#8 19.905       ", 19)
    l("#8 19.905       Error: pg_config executable not found.", 19)
    l("#8 19.905       ", 19)
    l("#8 19.905       pg_config is required to build psycopg2 from source.  Please add the directory", 19)
    l("#8 19.905       containing pg_config to the $PATH or specify the full executable path with the", 19)
    l("#8 19.905       option:", 19)
    l("#8 19.905           python setup.py build_ext --pg-config /path/to/pg_config build ...", 19)
    l("#8 19.905       If you prefer to avoid building psycopg2 from source, please install the PyPI", 19)
    l("#8 19.905       'psycopg2-binary' package instead.", 19)
    l("#8 19.905       [end of output]", 19)
    l("#8 19.907   note: This error originates from a subprocess, and is likely not a problem with pip.", 19)
    l("#8 19.911 error: metadata-generation-failed", 19)
    l("#8 ERROR: process \"/bin/sh -c pip install --no-cache-dir -r requirements.txt\" did not complete "
      "successfully: exit code: 1", 20)
    l("------", 20)
    l(" > [builder 4/4] RUN pip install --no-cache-dir -r requirements.txt:", 20)
    l("Dockerfile:4", 20)
    l("ERROR: failed to solve: process \"/bin/sh -c pip install --no-cache-dir -r requirements.txt\" did not "
      "complete successfully: exit code: 1", 20)
    l("##[error]Process completed with exit code 1.", 20)
    l("##[group]Post job cleanup.", 21)
    l("Cleaning up orphan processes", 21)
    return "\n".join(lineas)


LOG_CI = _log_ci()


# ---------------------------------------------------------------------------
# Caso 2: el plan de Terraform de un PR (formato de `terraform show -json`, recortado)
# ---------------------------------------------------------------------------
PR_TF = {"numero": 318, "titulo": "Cifrar la base de pedidos y abrir SSH para el bastión",
         "autor": "diego.r", "entorno": "produccion"}

PLAN_TF = {"format_version": "1.2", "terraform_version": "1.9.5", "resource_changes": [
    {"address": "aws_db_instance.pedidos", "type": "aws_db_instance", "name": "pedidos",
     "change": {"actions": ["delete", "create"], "replace_paths": [["storage_encrypted"]],
                "before": {"identifier": "pedidos-prod", "engine": "postgres", "engine_version": "16.3",
                           "instance_class": "db.r6g.large", "allocated_storage": 500, "storage_encrypted": False,
                           "multi_az": True, "deletion_protection": False, "skip_final_snapshot": True},
                "after": {"identifier": "pedidos-prod", "engine": "postgres", "engine_version": "16.3",
                          "instance_class": "db.t3.medium", "allocated_storage": 500, "storage_encrypted": True,
                          "multi_az": True, "deletion_protection": False, "skip_final_snapshot": True}}},
    {"address": "aws_security_group_rule.bastion_ssh", "type": "aws_security_group_rule", "name": "bastion_ssh",
     "change": {"actions": ["create"], "before": None,
                "after": {"type": "ingress", "from_port": 22, "to_port": 22, "protocol": "tcp",
                          "cidr_blocks": ["0.0.0.0/0"], "security_group_id": "sg-0a1b2c3d4e"}}},
    {"address": "aws_iam_role_policy.ci_deploy", "type": "aws_iam_role_policy", "name": "ci_deploy",
     "change": {"actions": ["update"],
                "before": {"policy": json.dumps({"Statement": [{"Effect": "Allow", "Action": ["ecr:*", "ecs:UpdateService"],
                                                                "Resource": "*"}]})},
                "after": {"policy": json.dumps({"Statement": [{"Effect": "Allow", "Action": ["ecr:*", "ecs:*", "iam:PassRole"],
                                                               "Resource": "*"}]})}}},
    {"address": "aws_s3_bucket_versioning.logs", "type": "aws_s3_bucket_versioning", "name": "logs",
     "change": {"actions": ["update"], "before": {"versioning_configuration": [{"status": "Suspended"}]},
                "after": {"versioning_configuration": [{"status": "Enabled"}]}}},
    {"address": "aws_cloudwatch_log_group.checkout", "type": "aws_cloudwatch_log_group", "name": "checkout",
     "change": {"actions": ["update"], "before": {"retention_in_days": 7}, "after": {"retention_in_days": 30}}},
]}


# ---------------------------------------------------------------------------
# Caso 3: un cluster de Kubernetes simulado (solo lectura)
# ---------------------------------------------------------------------------
_PODS = """NAME                        READY   STATUS             RESTARTS      AGE
checkout-6b8d5f7c9-lm2np    1/1     Running            0             3d2h
checkout-7d9f8c6b5-q8m3z    0/1     CrashLoopBackOff   6 (41s ago)   9m12s
checkout-7d9f8c6b5-x2k4p    0/1     CrashLoopBackOff   6 (38s ago)   9m12s
pagos-5f6c8d7b4-9vwxk       1/1     Running            0             6d
pagos-5f6c8d7b4-t7zq2       1/1     Running            0             6d
web-84c9b7d6f-2kd8s         1/1     Running            0             1d4h
web-84c9b7d6f-hx5nm         1/1     Running            0             1d4h"""

_DESCRIBE_NUEVO = """Name:         {pod}
Namespace:    tienda
Labels:       app=checkout
              pod-template-hash=7d9f8c6b5
Controlled By:  ReplicaSet/checkout-7d9f8c6b5
Containers:
  checkout:
    Image:          registry.clickit.dev/checkout:2.14.0
    Port:           8080/TCP
    State:          Waiting
      Reason:       CrashLoopBackOff
    Last State:     Terminated
      Reason:       Error
      Exit Code:    1
      Started:      Fri, 18 Sep 2026 03:08:51 -0500
      Finished:     Fri, 18 Sep 2026 03:08:52 -0500
    Ready:          False
    Restart Count:  6
    Limits:         cpu: 500m, memory: 512Mi
    Requests:       cpu: 250m, memory: 256Mi
    Readiness:      http-get http://:8080/health delay=5s period=10s
    Environment Variables from:
      checkout-config  ConfigMap  Optional: false
Events:
  Type     Reason   Age                   From     Message
  ----     ------   ----                  ----     -------
  Normal   Pulled   9m                    kubelet  Successfully pulled image "registry.clickit.dev/checkout:2.14.0"
  Normal   Started  8m (x4 over 9m)       kubelet  Started container checkout
  Warning  BackOff  41s (x39 over 8m55s)  kubelet  Back-off restarting failed container checkout"""

_DESCRIBE_VIEJO = """Name:         checkout-6b8d5f7c9-lm2np
Namespace:    tienda
Containers:
  checkout:
    Image:          registry.clickit.dev/checkout:2.13.2
    State:          Running
      Started:      Tue, 15 Sep 2026 01:04:10 -0500
    Ready:          True
    Restart Count:  0
    Environment Variables from:
      checkout-config  ConfigMap  Optional: false
Events:       <none>"""

_LOGS_NUEVO = """2026-09-18T08:08:51Z INFO  starting checkout 2.14.0
2026-09-18T08:08:51Z INFO  loading settings from environment
Traceback (most recent call last):
  File "/app/main.py", line 7, in <module>
    from checkout.settings import settings
  File "/app/checkout/settings.py", line 21, in <module>
    DATABASE_URL = os.environ["DATABASE_URL"]
                   ~~~~~~~~~~^^^^^^^^^^^^^^^^
  File "<frozen os>", line 714, in __getitem__
KeyError: 'DATABASE_URL'"""

_CONFIGMAP = """Name:         checkout-config
Namespace:    tienda
Data
====
DB_URL:
----
postgresql://checkout@pedidos-db.tienda.svc:5432/pedidos
LOG_LEVEL:
----
info
PAGOS_URL:
----
http://pagos.tienda.svc:8080"""

_HISTORIAL = """deployment.apps/checkout
REVISION  CHANGE-CAUSE
6         checkout 2.13.1: corrige redondeo de impuestos
7         checkout 2.13.2: timeouts de pagos configurables
8         checkout 2.14.0: renombra DB_URL a DATABASE_URL en settings (#412)"""

_EVENTOS = """LAST SEEN   TYPE      REASON              OBJECT                          MESSAGE
9m13s       Normal    ScalingReplicaSet   deployment/checkout             Scaled up replica set checkout-7d9f8c6b5 to 2
9m12s       Normal    Scheduled           pod/checkout-7d9f8c6b5-x2k4p    Successfully assigned tienda/checkout-7d9f8c6b5-x2k4p to node-3
9m12s       Normal    Scheduled           pod/checkout-7d9f8c6b5-q8m3z    Successfully assigned tienda/checkout-7d9f8c6b5-q8m3z to node-1
41s         Warning   BackOff             pod/checkout-7d9f8c6b5-q8m3z    Back-off restarting failed container checkout
38s         Warning   BackOff             pod/checkout-7d9f8c6b5-x2k4p    Back-off restarting failed container checkout
2m          Warning   ProgressDeadline    deployment/checkout             ReplicaSet "checkout-7d9f8c6b5" has timed out progressing"""


def _no_existe(tipo, nombre):
    return 'Error from server (NotFound): %s "%s" not found' % (tipo, nombre)


def get_pods(namespace="tienda"):
    """kubectl get pods -n <namespace>"""
    return _PODS if namespace == "tienda" else "No resources found in %s namespace." % namespace


def describe_pod(nombre):
    """kubectl describe pod <nombre> -n tienda"""
    if nombre.startswith("checkout-7d9f8c6b5-"):
        return _DESCRIBE_NUEVO.format(pod=nombre)
    if nombre == "checkout-6b8d5f7c9-lm2np":
        return _DESCRIBE_VIEJO
    return _no_existe("pods", nombre)


def logs(pod, previous=False):
    """kubectl logs <pod> -n tienda [--previous]"""
    if pod.startswith("checkout-7d9f8c6b5-"):
        return _LOGS_NUEVO
    if pod == "checkout-6b8d5f7c9-lm2np":
        return "2026-09-18T08:17:02Z INFO  POST /checkout 200 184ms\n2026-09-18T08:17:03Z INFO  POST /checkout 200 201ms"
    return _no_existe("pods", pod)


def get_events(namespace="tienda"):
    """kubectl get events -n <namespace> --sort-by=.lastTimestamp"""
    return _EVENTOS if namespace == "tienda" else "No resources found in %s namespace." % namespace


def rollout_history(deployment):
    """kubectl rollout history deployment/<deployment> -n tienda"""
    return _HISTORIAL if deployment == "checkout" else _no_existe("deployments.apps", deployment)


def get_configmap(nombre):
    """kubectl describe configmap <nombre> -n tienda"""
    return _CONFIGMAP if nombre == "checkout-config" else _no_existe("configmaps", nombre)


# ---------------------------------------------------------------------------
# Respuestas guardadas: si no hay clave, el notebook usa lo que respondio el modelo
# en una ejecucion real, en el mismo orden.
# ---------------------------------------------------------------------------
_ARCHIVO = RAIZ / "datos" / "respuestas_guardadas.json"
_usadas = {}


def respuesta_guardada(paso):
    guardadas = json.loads(_ARCHIVO.read_text(encoding="utf-8")) if _ARCHIVO.exists() else {}
    lista = guardadas.get(paso, [])
    n = _usadas.get(paso, 0)
    _usadas[paso] = n + 1
    if not lista:
        return {"role": "assistant", "content": "(no hay respuesta guardada para este paso)"}, (0, 0)
    r = lista[min(n, len(lista) - 1)]
    return r["mensaje"], (r["tokens_entrada"], r["tokens_salida"])


def grabar_respuestas(llamadas):
    """Uso interno: guarda las respuestas de una ejecucion real para usarlas sin clave."""
    guardadas = {}
    for f in llamadas:
        guardadas.setdefault(f["paso"], []).append({"mensaje": f["mensaje"], "tokens_entrada": f["tokens entrada"],
                                                     "tokens_salida": f["tokens salida"]})
    anteriores = json.loads(_ARCHIVO.read_text(encoding="utf-8")) if _ARCHIVO.exists() else {}
    anteriores.update(guardadas)       # sin pisar lo que grabó el otro notebook
    _ARCHIVO.write_text(json.dumps(anteriores, ensure_ascii=False, indent=1), encoding="utf-8")


def grabar_de_trazas(spans):
    """Uso interno: guarda las respuestas de una ejecucion real, por operacion y modelo."""
    guardadas = {}
    for s in spans:
        if "gen_ai.completion" not in s:
            continue
        clave = s["gen_ai.operation.name"] + "|" + s["gen_ai.request.model"]
        guardadas.setdefault(clave, []).append({"mensaje": s["gen_ai.completion"],
                                                "tokens_entrada": s["gen_ai.usage.input_tokens"],
                                                "tokens_salida": s["gen_ai.usage.output_tokens"]})
    anteriores = json.loads(_ARCHIVO.read_text(encoding="utf-8")) if _ARCHIVO.exists() else {}
    anteriores.update(guardadas)
    _ARCHIVO.write_text(json.dumps(anteriores, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(guardadas)
