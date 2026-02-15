# Semana 2: De Chatbots a Agentes 🤖

## 🎯 Objetivos de la Semana

Al finalizar esta semana, serás capaz de:

1. ✅ Comprender qué es un orquestador y por qué es necesario
2. ✅ Usar LangChain y LangGraph para construir aplicaciones de IA
3. ✅ Crear agentes inteligentes que pueden usar herramientas
4. ✅ Implementar razonamiento ReAct
5. ✅ Integrar LLMs con FastAPI
6. ✅ Construir un agente con búsqueda web

## 📚 Contenido

### Clase 1: Intro a LangChain
**Archivo**: `Clase_1_Intro_LangChain.ipynb`

**Temas cubiertos**:
- ¿Por qué necesitamos orquestadores?
- **LangChain**: Framework para aplicaciones con LLMs
- **LangGraph**: Flujos de trabajo complejos con grafos
- **Conceptos clave**:
  - Chains (Cadenas)
  - Runnables
  - Graphs (Grafos)
  - Paralelización vs Secuencial
- Integración con FastAPI y Uvicorn

**Práctica**:
- Crear chains básicas
- Implementar flujos paralelos y secuenciales
- Construir una API con LangChain

---

### Clase 2: Agentes y Herramientas (Tools)
**Archivo**: `Clase_2_Agentes_y_Tools.ipynb`

**Temas cubiertos**:
- **Agentes**: Sistemas que toman decisiones autónomas
- **ReAct**: Reasoning + Acting
- **Tools**: Herramientas que los agentes pueden usar
- **Chain of Thought**: Razonamiento paso a paso
- **Function Calling**: Conectar LLMs con funciones externas
- Búsqueda web con Tavily

**Práctica**:
- Crear un agente simple
- Implementar tools personalizadas
- Construir un agente con búsqueda web
- Debugging de agentes

## 📁 Estructura de Archivos

```
Semana_2/
├── README.md (este archivo)
├── Clase_1_Intro_LangChain.ipynb
├── Clase_2_Agentes_y_Tools.ipynb
├── .env.example
└── fastapi_app/
    ├── main.py
    └── requirements.txt
```

## 🛠️ Requisitos Específicos

### Cuentas Necesarias

1. **LangChain/LangSmith** (Opcional pero recomendado)
   - Crear cuenta en: https://smith.langchain.com/
   - Obtener API key para tracing

2. **Tavily** (Para búsqueda web)
   - Crear cuenta en: https://tavily.com/
   - Plan gratuito disponible

### Instalación

```bash
pip install langchain langchain-openai langgraph langsmith tavily-python fastapi uvicorn
```

## 💡 Tips para Esta Semana

1. **Experimenta con chains**: Combina diferentes componentes
2. **Debug con LangSmith**: Usa tracing para entender qué hace tu agente
3. **Prueba diferentes tools**: Crea tus propias herramientas personalizadas
4. **Itera en los prompts**: Los agentes son sensibles a cómo describes las tools

## 🎯 Proyecto Sugerido

**Mini-proyecto de la semana**: Crear un agente asistente personal que puede:
- Buscar información en la web
- Realizar cálculos
- Guardar notas
- Responder preguntas usando RAG (combinando Semana 1 y 2)

## ❓ Preguntas Frecuentes

**P: ¿Cuál es la diferencia entre LangChain y LangGraph?**  
R: LangChain es para flujos lineales o simples. LangGraph permite crear flujos complejos con ramificaciones, loops, y decisiones condicionales.

**P: ¿Los agentes son confiables?**  
R: Los agentes pueden cometer errores. Es importante implementar validación, límites de iteraciones, y supervisión humana cuando sea necesario.

**P: ¿Tavily es gratuito?**  
R: Tavily tiene un plan gratuito con límites. Para el taller es suficiente.

---

**¡Vamos a construir agentes inteligentes! 🚀**
