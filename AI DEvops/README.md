# Taller AI DevOps - 5 sesiones

- `Taller_AI_DevOps_5_Sesiones (3).pptx` - la presentacion.
- `laboratorios/` - los ejercicios ejecutables, uno por sesion.

## Para los asistentes

```bash
cd laboratorios
pip install -r requirements.txt
python verificar_entorno.py
jupyter notebook
```

Y abre `notebooks/Sesion_1_Fundamentos_y_Arquitectura.ipynb`.

**No hace falta API key ni tarjeta**: los laboratorios traen un proveedor simulado que
imita el comportamiento de un LLM real (no determinismo, formato roto, alucinacion,
costo, latencia, fallos e inyeccion de prompt). Ver `laboratorios/README.md`.
