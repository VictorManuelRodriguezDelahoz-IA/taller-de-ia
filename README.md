# Taller de IA: From Zero to Hero 🚀

Bienvenido al taller intensivo de Inteligencia Artificial de **Clicit**. Este programa de 4 semanas te llevará desde los conceptos fundamentales hasta el desarrollo de productos con IA listos para producción.

## 📋 Información General

- **Duración**: 4 semanas (8 sesiones)
- **Formato**: 2 clases por semana (1.5 - 2 horas cada una)
- **Nivel**: Básico a Intermedio
- **Objetivo**: Construir un portafolio con al menos 1 proyecto (RAG/Agentes) y estar preparado para Hackathons

## 🎯 Objetivos del Taller

Al finalizar este taller, serás capaz de:

1. ✅ Comprender cómo funcionan los LLMs y aplicar técnicas de prompt engineering
2. ✅ Implementar sistemas RAG (Retrieval Augmented Generation)
3. ✅ Crear agentes inteligentes con herramientas
4. ✅ Desarrollar sistemas multi-agente complejos
5. ✅ Desplegar productos de IA en producción
6. ✅ Tener un proyecto completo en tu portafolio

## 📚 Estructura del Taller

### Semana 1: Los Cimientos (LLMs & RAG)
**Clase 1: Prompt Engineering & Vibe Check**
- Cómo funcionan los LLMs
- Conceptos: temperatura, top-P, top-K, tokens, tokenization
- Context window y memoria
- Técnicas de prompt engineering

**Clase 2: Chat con tus Datos (RAG Básico)**
- Embeddings y modelos de embedding
- Búsqueda semántica vs búsqueda por palabras clave
- Chunking, retrieval, augmentation, generation
- Instalación de LLAMA local
- Casos de uso de RAG

### Semana 2: De Chatbots a Agentes
**Clase 1: Intro a LangChain**
- ¿Por qué necesitamos un orquestador?
- LangChain vs LangGraph
- Chains, Runnables, Graphs
- Paralelización vs ejecución secuencial
- Integración con FastAPI

**Clase 2: Agentes y Herramientas (Tools)**
- Conceptos de agentes
- Razonamiento ReAct
- Tools y function calling
- Chain of thought
- Práctica: Agente con búsqueda web (Tavily)

### Semana 3: Profundización
**Clase 1: LangGraph & LangSmith**
- Graphs, nodes, edges
- State management y memoria
- Function calling avanzado
- Monitoreo con LangSmith

**Clase 2: Sistemas Multi-Agente**
- Arquitecturas multi-agente
- Patrones de comunicación
- Casos de uso
- Templates de agentes

### Semana 4: Deployment de Producto con AI
**Clase 1: Testing para LLMs**
- Estrategias de testing
- Métricas de evaluación
- Best practices de deployment
- Documentación de productos de IA

**Clase 2: Demo Day**
- Presentación de proyectos finales
- Preparación para Hackathons
- Portfolio building

## 🛠️ Requisitos Previos

### Software Necesario
- Python 3.9 o superior
- Jupyter Notebook o Google Colab
- Git
- Editor de código (VS Code recomendado)

### Conocimientos Recomendados
- Python básico
- Conceptos básicos de programación
- Familiaridad con APIs (deseable)

## 📦 Instalación

### 1. Clonar el Repositorio
```bash
git clone <repository-url>
cd "Taller de IA"
```

### 2. Crear Entorno Virtual
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno
Copia el archivo `.env.example` a `.env` y configura tus API keys:
```bash
cp .env.example .env
```

## 🔑 API Keys Necesarias

A lo largo del taller necesitarás crear cuentas y obtener API keys para:

- **OpenAI** o **Anthropic**: Para usar LLMs (Semana 1)
- **Tavily**: Para búsqueda web con agentes (Semana 2)
- **LangChain/LangSmith**: Para orquestación y monitoreo (Semanas 2-3)

> **Nota**: Algunas de estas herramientas ofrecen planes gratuitos o trials. Verifica los requisitos antes de cada clase.

## 📖 Cómo Usar Este Material

Cada semana tiene su propia carpeta con:

1. **README.md**: Objetivos y resumen de la semana
2. **Notebooks (.ipynb)**: Material interactivo para cada clase
3. **Scripts**: Código auxiliar y templates
4. **Data**: Datos de ejemplo para prácticas

### Flujo de Trabajo Recomendado

1. 📖 Lee el README de la semana
2. 🎓 Asiste a la clase o sigue el notebook
3. ▶️ Ejecuta cada celda del notebook
4. ✏️ Personaliza los ejemplos con tus propios datos
5. 🏋️ Completa los ejercicios prácticos
6. 🚀 Experimenta y construye tus propias variaciones

## 🎓 Estructura de los Notebooks

Todos los notebooks siguen esta estructura:

1. **Introducción**: Objetivos y conceptos clave
2. **Teoría**: Explicación de conceptos con ejemplos visuales
3. **Práctica Guiada**: Código paso a paso con explicaciones
4. **Ejercicios**: Actividades para personalizar y experimentar
5. **Recursos Adicionales**: Links y referencias para profundizar

## 💡 Tips para Aprovechar el Taller

- ✅ **Practica activamente**: No solo leas, ejecuta y modifica el código
- ✅ **Haz preguntas**: Usa los espacios de discusión
- ✅ **Documenta tu aprendizaje**: Toma notas y crea tu propio repositorio
- ✅ **Construye tu proyecto**: Desde la semana 1, piensa en qué quieres construir
- ✅ **Colabora**: Comparte ideas con otros participantes

## 🚀 Proyecto Final

Durante el taller, trabajarás en un proyecto personal que puede ser:

- Sistema RAG para documentación técnica
- Asistente virtual con múltiples herramientas
- Sistema multi-agente para automatización
- Chatbot especializado en tu dominio

## 📞 Soporte

- **Dudas técnicas**: [Canal de soporte]
- **Issues del código**: Abre un issue en el repositorio
- **Discusiones**: [Foro de discusión]

## 📄 Licencia

Este material es propiedad de **Clicit** y está diseñado para uso educativo en el contexto del taller.

---

**¡Prepárate para convertirte en un AI Hero! 🦸‍♂️🦸‍♀️**
