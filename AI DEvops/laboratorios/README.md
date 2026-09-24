# Laboratorios - Taller AI DevOps (ClickIT)

Cinco notebooks, uno por sesion, para **ejecutar** lo que se explica en la presentacion
`Taller_AI_DevOps_5_Sesiones.pptx`.

La idea es sencilla: cada concepto de las diapositivas tiene aqui una celda que lo
demuestra en tu maquina, y un ejercicio corto con un `TODO` para que lo toques tu.

## Arranque rapido (3 minutos)

```bash
cd "AI DEvops/laboratorios"
pip install -r requirements.txt
python verificar_entorno.py
jupyter notebook          # o abre la carpeta en VS Code
```

**No necesitas ninguna API key, ni tarjeta, ni cuenta.** Los laboratorios usan un
proveedor simulado (`sim-small` y `sim-large`) que imita el comportamiento real de un
LLM: no es determinista, rompe el formato si no se lo exiges, inventa datos cuando no
los tiene, obedece inyecciones de prompt si no lo defiendes, cuesta dinero, tarda y a
veces se cae.

> Es un simulador **didactico**: para los casos del set dorado conoce la etiqueta
> correcta, y lo que decide si acierta o no es la calidad de tu prompt y la ambiguedad
> del caso. Eso es justo lo que queremos que midas.

### Con modelos reales (opcional)

```bash
cp .env.example .env      # y pon tu clave
```

Luego cambia `MODELO = "sim-small"` por `"gpt-4o-mini"` o `"claude-haiku-4-5-20251001"`
en la primera celda. El resto del notebook no cambia: todo pasa por `chat()`, que es el
gateway. Anade los precios vigentes de ese modelo al diccionario `PRECIOS` de
`lab_utils.py` para que el calculo de costo siga siendo real.

## Las cinco sesiones

| Notebook | Sesion | Al terminar tienes |
|---|---|---|
| `Sesion_1_Fundamentos_y_Arquitectura.ipynb` | Fundamentos y arquitectura | Bucle con frenos, grafo con estado y gateway con ruteo en cascada |
| `Sesion_2_Prompts_y_Evaluacion.ipynb` | Prompts y evaluacion | Corregir un examen de 40 tickets, comparar versiones de prompt, romper una a proposito y medir las manias del juez LLM |
| `Sesion_3_CICD_y_Observabilidad.ipynb` | CI/CD y observabilidad | Trazas con esquema, un gate que bloquea de verdad, canario y rollback |
| `Sesion_4_Costo_Latencia_Resiliencia.ipynb` | Costo, latencia y resiliencia | Costo por tenant, tres capas de cache y un fallback probado |
| `Sesion_5_Seguridad_y_Operacion.ipynb` | Seguridad y operacion | Red team de 15 casos y un runbook con responsables |
| `Lab_IA_para_DevOps.ipynb` | IA en el día a día de DevOps (1 hora) | Tres casos con un modelo real vía OpenRouter: diagnosticar un pipeline roto, revisar un plan de Terraform y un agente de guardia con herramientas de Kubernetes de solo lectura. Necesita `OPENROUTER_API_KEY` en `.env`; sin clave usa respuestas guardadas de una ejecución real |
| `Proyecto_Final_Copiloto_DevOps.ipynb` | Proyecto final: todo junto (2 horas) | Un bot que recibe cualquier evento y lo atiende: router en cascada con modelos abiertos, diagnóstico de un log de CI **real** bajado con `gh`, revisión de un `terraform plan` **real**, agente con servidor MCP, enmascarado de secretos, evaluación con set dorado, gate y costo por evento. `gh` y `terraform` son opcionales: sin ellos usa datos guardados |

Cada notebook dura entre 45 y 70 minutos si se hacen los ejercicios. Se pueden correr
de forma independiente: **no hace falta haber terminado el anterior**.

## Que hay en la carpeta

```
laboratorios/
  lab_utils.py                el proveedor simulado, el conteo de tokens, costo y trazas
  devops_ia.py                datos del laboratorio de IA para DevOps (log de CI, plan de Terraform, cluster)
  copiloto.py                 kit del proyecto final: secretos, inyeccion, servidor MCP, set dorado y trazas
  eval.py                     el gate del proyecto final, para correr en CI (exit 1 si baja la calidad)
  terraform_demo/             modulo de Terraform con providers locales, para correr un plan de verdad
  aiops.py                    tarjetas, tablas y graficos que usa ese laboratorio
  evaluador.py                el runner de evaluacion (se construye en la Sesion 2)
  ci_eval.py                  el comando que corre en CI y devuelve exit code 1
  gate.yaml                   los umbrales del gate. El contrato del equipo
  github-workflow-ejemplo.yml el pipeline listo para copiar a tu repositorio
  verificar_entorno.py        comprobacion previa
  prompts/                    el mismo prompt en tres versiones (v1, v2 y una rota)
  datos/
    golden_incidentes.jsonl   40 casos: 60% tipicos, 30% dificiles, 10% de rechazo
    red_team.jsonl            15 casos adversarios
    documentos/               runbook, politica de datos y dos documentos contaminados
  notebooks/                  los cinco laboratorios
  resultados/                 lo que generan los notebooks (baseline, runbook, evals)
  _fuente/                    el codigo fuente de los notebooks en formato .py
```

### Regenerar los notebooks

Los notebooks se generan desde `_fuente/*.py`. Si prefieres editar el `.py`:

```bash
python _fuente/mknb.py _fuente/sesion1.py notebooks/Sesion_1_Fundamentos_y_Arquitectura.ipynb
```

Tambien puedes ejecutar un laboratorio entero sin Jupyter, para comprobar que todo
sigue funcionando: `python _fuente/sesion3.py`.

## El hilo conductor

Los cinco laboratorios trabajan sobre **el mismo caso**: clasificar tickets de
incidentes en categoria, severidad, servicio y si requiere intervencion humana.

Es a proposito. El mismo sistema se evalua (S2), se mete en un gate (S3), se abarata
(S4) y se ataca (S5). Cuando cambies el set dorado por el de tu equipo, los cinco
notebooks siguen funcionando.

## Sustituirlo por tu caso de uso

1. Reemplaza `datos/golden_incidentes.jsonl` por tus 20-30 casos, mismo formato:
   ```json
   {"id": "CASO-001", "entrada": "...", "esperado": {...}, "dificultad": "tipico"}
   ```
2. Reescribe `prompts/clasificar_incidente.v1.yaml` con tu prompt.
3. Corre `python ci_eval.py --guardar-baseline` y anota tu puntaje base.
4. A partir de ahi, los cinco notebooks miden **tu** sistema.

## Preguntas frecuentes

**`pip install` falla en Windows** con `No such file or directory` o un aviso de
*Long Path*. Es el limite de 260 caracteres de las rutas de Windows: clona el repo en una
carpeta corta (por ejemplo `C:\taller`) y vuelve a instalar. `python verificar_entorno.py`
te avisa si la instalacion quedo a medias.

**No tengo Jupyter.** Abre la carpeta en VS Code con la extension de Python: los
`.ipynb` se ejecutan directamente. O corre los `_fuente/*.py` desde la terminal.

**Una celda tarda mucho.** Baja `LAB_VELOCIDAD` en el `.env` (o exporta
`LAB_VELOCIDAD=0`) para que el simulador no espere la latencia simulada.

**Me sale un resultado distinto al del README.** Correcto: el sistema no es
determinista. Esa es la primera leccion de la Sesion 1.

**Los ejercicios no tienen solucion en el notebook.** Estan en `SOLUCIONES.md`.
Mirala despues de intentarlo, no antes.
