# Semana 1: Los Cimientos (LLMs & RAG) 🏗️

## 🎯 Objetivos de la Semana

Al finalizar esta semana, serás capaz de:

1. ✅ Comprender cómo funcionan los Large Language Models (LLMs)
2. ✅ Aplicar técnicas efectivas de prompt engineering
3. ✅ Entender conceptos clave: temperatura, tokens, context window
4. ✅ Implementar un sistema RAG básico
5. ✅ Trabajar con embeddings y búsqueda semántica
6. ✅ Instalar y usar LLAMA localmente

## 📚 Contenido

### Clase 1: Prompt Engineering & Vibe Check
**Archivo**: `Clase_1_Prompt_Engineering.ipynb`

**Temas cubiertos**:
- ¿Qué es un LLM y cómo funciona?
- Conceptos fundamentales:
  - **Temperatura**: Control de creatividad vs determinismo
  - **Top-P y Top-K**: Estrategias de muestreo
  - **Tokens**: La unidad básica de los LLMs
  - **Tokenization**: Cómo el texto se convierte en números
  - **Context Window**: Límites de memoria del modelo
- Técnicas de prompt engineering
- Mejores prácticas y patrones comunes

**Práctica**:
- Experimentar con diferentes temperaturas
- Crear prompts efectivos para diferentes tareas
- Analizar tokenización de diferentes textos

---

### Clase 2: Chat con tus Datos (RAG Básico)
**Archivo**: `Clase_2_RAG_Basico.ipynb`

**Temas cubiertos**:
- **Embeddings**: Transformar texto en vectores numéricos
- **Modelos de embedding**: Sentence Transformers, OpenAI Embeddings
- **Chunking**: Estrategias para dividir documentos
- **Búsqueda semántica** vs búsqueda por palabras clave
- **Pipeline RAG**:
  1. Retrieval (Recuperación)
  2. Augmentation (Aumentación)
  3. Generation (Generación)
- Casos de uso: ¿Cuándo usar RAG?
- Instalación de LLAMA local

**Práctica**:
- Crear embeddings de documentos
- Implementar búsqueda semántica
- Construir un sistema RAG completo
- Migrar datos a una base de datos vectorial

## 📁 Estructura de Archivos

```
Semana_1/
├── README.md (este archivo)
├── Clase_1_Prompt_Engineering.ipynb
├── Clase_2_RAG_Basico.ipynb
├── diccionario_ia.md
├── data/
│   └── sample_documents.txt
└── scripts/
    └── db_migration.py
```

## 🛠️ Requisitos Específicos

### Instalación Adicional para LLAMA Local

```bash
# Para CPU
pip install llama-cpp-python

# Para GPU (NVIDIA)
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python
```

### Descargar Modelo LLAMA

Instrucciones detalladas en `Clase_2_RAG_Basico.ipynb`

## 📖 Recursos Adicionales

- **Diccionario de IA**: `diccionario_ia.md` - Glosario de términos
- **Documentación OpenAI**: https://platform.openai.com/docs
- **Guía de Prompt Engineering**: https://www.promptingguide.ai/
- **LangChain Docs**: https://python.langchain.com/docs

## 💡 Tips para Esta Semana

1. **Experimenta con temperatura**: Prueba valores entre 0 y 2 para ver cómo cambia el comportamiento
2. **Cuenta tokens**: Usa herramientas como tiktoken para entender el consumo
3. **Prueba diferentes chunking strategies**: El tamaño del chunk afecta la calidad del RAG
4. **Compara búsquedas**: Haz la misma consulta con búsqueda semántica y keyword search

## 🎯 Proyecto Sugerido

**Mini-proyecto de la semana**: Crear un chatbot que responda preguntas sobre un conjunto de documentos de tu elección (PDFs, artículos, documentación técnica, etc.)

## ❓ Preguntas Frecuentes

**P: ¿Necesito GPU para LLAMA local?**  
R: No es obligatorio, pero mejora significativamente el rendimiento. Puedes usar modelos más pequeños en CPU.

**P: ¿Cuánto cuesta usar las APIs?**  
R: OpenAI y Anthropic tienen pricing por tokens. Para el taller, con $5-10 USD es suficiente.

**P: ¿Puedo usar Google Colab?**  
R: ¡Sí! Todos los notebooks funcionan en Colab. Algunos incluyen botones de "Open in Colab".

---

**¡Vamos a construir los cimientos de tu conocimiento en IA! 🚀**
