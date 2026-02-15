# Semana 3: Profundización 🚀

## 🎯 Objetivos de la Semana

Al finalizar esta semana, serás capaz de:

1. ✅ Dominar LangGraph para flujos complejos
2. ✅ Implementar state management y memoria
3. ✅ Usar LangSmith para monitoreo y debugging
4. ✅ Diseñar arquitecturas multi-agente
5. ✅ Crear sistemas de agentes colaborativos
6. ✅ Aplicar patrones avanzados de IA

## 📚 Contenido

### Clase 1: Profundización en LangGraph & LangSmith
**Archivo**: `Clase_1_LangGraph_LangSmith.ipynb`

**Temas cubiertos**:
- **LangGraph en profundidad**:
  - Graphs (Grafos)
  - Nodes (Nodos)
  - Edges (Conexiones)
  - Conditional edges
  - State management
  - Memory y persistencia
- **Function Calling avanzado**
- **LangSmith**:
  - Tracing y debugging
  - Evaluación de prompts
  - Monitoreo en producción
  - Análisis de costos

**Práctica**:
- Crear grafos con decisiones condicionales
- Implementar memoria persistente
- Usar LangSmith para optimizar prompts
- Construir flujos complejos con múltiples caminos

---

### Clase 2: Sistemas Multi-Agente
**Archivo**: `Clase_2_Sistemas_Multi_Agente.ipynb`

**Temas cubiertos**:
- **Arquitecturas multi-agente**:
  - Jerárquicas
  - Colaborativas
  - Competitivas
  - Especializadas
- **Patrones de comunicación**
- **Coordinación entre agentes**
- **Casos de uso reales**
- **System prompts avanzados**

**Práctica**:
- Crear un sistema con múltiples agentes especializados
- Implementar coordinación entre agentes
- Construir un equipo de agentes para resolver problemas complejos

## 📁 Estructura de Archivos

```
Semana_3/
├── README.md (este archivo)
├── Clase_1_LangGraph_LangSmith.ipynb
├── Clase_2_Sistemas_Multi_Agente.ipynb
└── templates/
    ├── agent_template.py
    └── multi_agent_template.py
```

## 🛠️ Requisitos Específicos

### LangSmith Setup

```bash
# Variables de entorno necesarias
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_api_key
LANGCHAIN_PROJECT=taller-ia-semana3
```

### Instalación

```bash
pip install langgraph langsmith langchain-openai
```

## 💡 Tips para Esta Semana

1. **Visualiza tus grafos**: LangGraph puede generar diagramas de tus flujos
2. **Usa LangSmith desde el inicio**: El tracing te ahorrará mucho tiempo de debugging
3. **Diseña antes de codear**: Los sistemas multi-agente requieren planificación
4. **Empieza simple**: Agrega complejidad gradualmente
5. **Testea cada agente individualmente**: Antes de integrarlos

## 🎯 Proyecto Sugerido

**Mini-proyecto de la semana**: Crear un sistema multi-agente para investigación que incluya:
- **Agente Investigador**: Busca información en la web
- **Agente Analista**: Procesa y analiza la información
- **Agente Escritor**: Genera reportes estructurados
- **Agente Coordinador**: Orquesta el flujo de trabajo

## 📊 Arquitecturas Multi-Agente Comunes

### 1. Jerárquica
```
Coordinador
    ├── Agente A
    ├── Agente B
    └── Agente C
```

### 2. Pipeline
```
Agente A → Agente B → Agente C → Resultado
```

### 3. Colaborativa
```
    Agente A
       ↓↑
    Agente B  ←→  Agente C
       ↓↑
    Resultado
```

## ❓ Preguntas Frecuentes

**P: ¿Cuándo usar multi-agente vs un solo agente?**  
R: Usa multi-agente cuando:
- Las tareas son claramente separables
- Necesitas especialización
- Quieres paralelizar el trabajo
- El problema es muy complejo para un solo agente

**P: ¿Los agentes pueden comunicarse entre sí?**  
R: Sí, pueden compartir estado, pasar mensajes, o trabajar en un estado compartido.

**P: ¿Cómo evito loops infinitos en grafos?**  
R: Implementa límites de iteraciones, condiciones de salida claras, y monitoreo con LangSmith.

---

**¡Vamos a construir sistemas de IA de nivel profesional! 🚀**
