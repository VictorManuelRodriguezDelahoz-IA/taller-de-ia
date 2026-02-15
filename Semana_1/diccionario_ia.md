# 📖 Diccionario de Inteligencia Artificial

Glosario de términos clave para el Taller de IA "From Zero to Hero"

---

## A

### Agent (Agente)
Sistema de IA que puede tomar decisiones y ejecutar acciones de forma autónoma para lograr objetivos específicos. Puede usar herramientas y razonar sobre qué pasos seguir.

### API (Application Programming Interface)
Interfaz que permite que diferentes aplicaciones se comuniquen entre sí. En IA, usamos APIs para acceder a modelos como GPT-4 o Claude.

### Augmentation (Aumentación)
En RAG, es el proceso de enriquecer el prompt con información recuperada de una base de conocimiento.

---

## C

### Chain (Cadena)
En LangChain, una secuencia de operaciones que se ejecutan en orden. Por ejemplo: procesar input → llamar LLM → formatear output.

### Chain of Thought (Cadena de Pensamiento)
Técnica de prompting que pide al modelo que muestre su razonamiento paso a paso antes de dar una respuesta final.

### Chunking
Proceso de dividir documentos largos en fragmentos más pequeños para procesamiento más eficiente. Esencial en sistemas RAG.

### Context Window (Ventana de Contexto)
Cantidad máxima de tokens que un modelo puede procesar en una sola interacción. Incluye tanto el prompt como la respuesta.

---

## E

### Embedding
Representación numérica (vector) de texto que captura su significado semántico. Textos similares tienen embeddings similares.

### Embedding Model
Modelo especializado en convertir texto en embeddings. Ejemplos: sentence-transformers, OpenAI text-embedding-ada-002.

---

## F

### Few-Shot Learning
Técnica donde se proporcionan algunos ejemplos en el prompt para que el modelo aprenda el patrón deseado.

### Fine-tuning
Proceso de entrenar un modelo pre-entrenado con datos específicos para especializarlo en una tarea particular.

### Function Calling
Capacidad de un LLM para invocar funciones o herramientas externas basándose en el contexto de la conversación.

---

## G

### Generation (Generación)
En RAG, es el paso final donde el LLM genera una respuesta usando el contexto recuperado.

### Graph
En LangGraph, estructura que define flujos de trabajo complejos con nodos y conexiones entre ellos.

---

## H

### Hallucination (Alucinación)
Cuando un LLM genera información falsa o inventada que presenta como verdadera. RAG ayuda a reducir esto.

---

## L

### LangChain
Framework para desarrollar aplicaciones con LLMs. Facilita la creación de cadenas, agentes y flujos complejos.

### LangGraph
Extensión de LangChain para crear flujos de trabajo con grafos, permitiendo lógica más compleja y ramificada.

### LangSmith
Plataforma para monitorear, debuggear y evaluar aplicaciones construidas con LangChain.

### LLM (Large Language Model)
Modelo de IA entrenado con enormes cantidades de texto para entender y generar lenguaje natural.

---

## M

### Max Tokens
Número máximo de tokens que el modelo puede generar en su respuesta.

### Multi-Agent System (Sistema Multi-Agente)
Arquitectura donde múltiples agentes de IA trabajan juntos, cada uno con roles y responsabilidades específicas.

---

## N

### Node (Nodo)
En LangGraph, un punto en el grafo que ejecuta una operación específica (llamar LLM, procesar datos, etc.).

### Nucleus Sampling
Ver Top-P.

---

## P

### Prompt
Instrucción o pregunta que se le da a un LLM para obtener una respuesta.

### Prompt Engineering
Arte y ciencia de diseñar prompts efectivos para obtener mejores resultados de los LLMs.

---

## R

### RAG (Retrieval Augmented Generation)
Técnica que combina búsqueda de información con generación de texto. El modelo busca información relevante antes de generar una respuesta.

### ReAct (Reasoning + Acting)
Patrón donde el agente alterna entre razonar sobre qué hacer y ejecutar acciones.

### Retrieval (Recuperación)
Proceso de buscar y obtener información relevante de una base de conocimiento.

### Runnable
En LangChain, cualquier componente que puede ser ejecutado (chains, LLMs, tools, etc.).

---

## S

### Semantic Search (Búsqueda Semántica)
Búsqueda basada en el significado del texto, no solo en palabras clave. Usa embeddings para encontrar contenido similar.

### Similarity Search (Búsqueda por Similitud)
Encontrar documentos o fragmentos de texto más similares a una consulta usando embeddings.

### State (Estado)
En LangGraph, información que se mantiene y actualiza a medida que el grafo se ejecuta.

### System Prompt
Instrucción inicial que define el comportamiento general del modelo (su "rol" o "personalidad").

---

## T

### Temperature (Temperatura)
Parámetro que controla la aleatoriedad de las respuestas del LLM. Valores bajos (0-0.3) son más deterministas, valores altos (0.8-2) más creativos.

### Token
Unidad básica de texto que procesan los LLMs. Puede ser una palabra, parte de una palabra, o un carácter.

### Tokenization (Tokenización)
Proceso de convertir texto en tokens que el modelo puede procesar.

### Tool (Herramienta)
Función o API externa que un agente puede usar para realizar tareas específicas (buscar en web, hacer cálculos, etc.).

### Top-K
Parámetro que limita la selección del siguiente token a los K más probables.

### Top-P (Nucleus Sampling)
Parámetro que selecciona tokens cuya probabilidad acumulada alcanza P. Controla la diversidad de las respuestas.

---

## V

### Vector Database (Base de Datos Vectorial)
Base de datos optimizada para almacenar y buscar embeddings. Ejemplos: ChromaDB, Pinecone, FAISS.

### Vector Store
Ver Vector Database.

---

## Z

### Zero-Shot Learning
Capacidad del modelo de realizar tareas sin ejemplos previos, solo con instrucciones en el prompt.

---

## Símbolos y Abreviaturas

### API Key
Clave de autenticación para acceder a servicios de IA.

### GPU (Graphics Processing Unit)
Procesador especializado que acelera el entrenamiento y ejecución de modelos de IA.

### JSON (JavaScript Object Notation)
Formato de datos estructurado comúnmente usado para intercambiar información con APIs.

### NLP (Natural Language Processing)
Procesamiento de Lenguaje Natural - campo de IA enfocado en entender y generar lenguaje humano.

---

## Recursos para Profundizar

- **OpenAI Glossary**: https://platform.openai.com/docs/guides/glossary
- **LangChain Concepts**: https://python.langchain.com/docs/concepts
- **Hugging Face NLP Course**: https://huggingface.co/learn/nlp-course

---

*Este diccionario se actualiza continuamente. Si encuentras un término que no está aquí, ¡avísanos!*
