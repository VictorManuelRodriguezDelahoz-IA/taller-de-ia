# Guía: Embeddings, Chunking y RAG en Producción

> Documento de referencia para el taller. Incluye buenas prácticas reales
> y el modelo **`cohere_v4_embedding`** que usamos en producción.

---

## 1. Embeddings — ¿Qué modelo usar?

Un embedding convierte texto en un vector numérico que captura su significado.
Elegir el modelo correcto impacta directamente en la calidad de tu RAG.

### Comparativa de modelos

| Modelo | Proveedor | Dims | Costo | Multilingüe | Cuándo usarlo |
|---|---|---|---|---|---|
| `embed-v4.0` (cohere_v4_embedding) | Cohere | 1024 | De pago | ✅ | **Producción, alta calidad** |
| `text-embedding-3-small` | OpenAI | 1536 | De pago | ✅ | Proyectos en ecosistema OpenAI |
| `text-embedding-3-large` | OpenAI | 3072 | De pago | ✅ | Máxima calidad OpenAI |
| `paraphrase-multilingual-MiniLM-L12-v2` | HuggingFace | 384 | **Gratis** | ✅ | Aprendizaje, prototipos |
| `all-MiniLM-L6-v2` | HuggingFace | 384 | **Gratis** | ❌ (solo inglés) | Proyectos en inglés, muy rápido |
| `bge-large-en-v1.5` | HuggingFace / BAAI | 1024 | **Gratis** | ❌ | Inglés de alta calidad sin costo |

### El modelo de José: `cohere_v4_embedding` (embed-v4.0)

Cohere `embed-v4.0` es el modelo de embeddings más avanzado de Cohere a la fecha.
Sus puntos fuertes para producción:

- **Multimodal**: entiende texto e imágenes en el mismo espacio vectorial
- **Multilingüe**: funciona bien en español, inglés y más de 100 idiomas
- **Input types**: permite especificar si el texto es un documento o una query,
  lo que mejora la precisión de la búsqueda
- **Dimensiones reducibles**: soporta 256, 512 y 1024 dims para balance costo/calidad

```python
# Uso de cohere_v4_embedding con LangChain
from langchain_cohere import CohereEmbeddings

embeddings = CohereEmbeddings(
    model="embed-v4.0",
    cohere_api_key=os.getenv("COHERE_API_KEY"),
    input_type="search_document",   # Para indexar documentos
    # input_type="search_query"     # Para consultas del usuario
)

# En ChromaDB
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    collection_name="mi_coleccion"
)
```

> **Tip clave**: Cohere diferencia entre `search_document` (al indexar) y
> `search_query` (al buscar). Usar el tipo correcto mejora la relevancia
> de forma significativa.

### Regla práctica

```
Prototipo / sin presupuesto  →  HuggingFace (local, gratis)
Producción en español        →  Cohere embed-v4.0 (mejor calidad multilingüe)
Ecosistema OpenAI            →  text-embedding-3-small (buena relación calidad/precio)
```

---

## 2. Chunking — La base de un RAG que funciona

El chunking es dividir documentos largos en fragmentos más pequeños antes de
generar embeddings. **Es la decisión más crítica en un pipeline RAG**.

### Por qué importa

- Chunks muy grandes → búsqueda poco precisa, contexto ruidoso
- Chunks muy pequeños → pierdes contexto, fragmentas ideas
- El overlap evita perder información en los bordes de cada chunk

### Estrategias de chunking

#### 1. RecursiveCharacterTextSplitter (recomendada para la mayoría de casos)

Intenta dividir por párrafos, luego por oraciones, luego por palabras.
Es la estrategia más robusta para texto genérico.

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,        # ~375 tokens (1 token ≈ 1.3 caracteres en español)
    chunk_overlap=50,      # 10% de overlap — regla general
    separators=["\n\n", "\n", ". ", " ", ""]
)
```

#### 2. Chunking por tokens (más preciso para límites de contexto)

```python
from langchain.text_splitter import TokenTextSplitter

splitter = TokenTextSplitter(
    chunk_size=300,    # tokens reales
    chunk_overlap=30
)
```

#### 3. Chunking semántico (avanzado)

Agrupa oraciones que hablan del mismo tema antes de dividir.
Disponible en `langchain_experimental`.

```python
from langchain_experimental.text_splitter import SemanticChunker

splitter = SemanticChunker(
    embeddings=embeddings_model,
    breakpoint_threshold_type="percentile"
)
```

### Tabla de referencia: ¿qué tamaño usar?

| Tipo de documento | chunk_size | chunk_overlap | Notas |
|---|---|---|---|
| FAQs / preguntas cortas | 100–200 tokens | 10–20 | Cada Q&A en su chunk |
| Artículos / documentación | 300–500 tokens | 50 | El más común |
| PDFs técnicos / legales | 400–600 tokens | 80 | Contexto es clave |
| Código fuente | Por función | 0–10 | Dividir por función, no por caracteres |
| Correos / mensajes | 150–300 tokens | 20 | Textos cortos de por sí |

### Buenas prácticas de chunking

1. **Agrega metadata siempre** — te permite filtrar y citar fuentes:
   ```python
   Document(
       page_content=chunk,
       metadata={
           "source": "manual_usuario.pdf",
           "page": 12,
           "section": "Instalación",
           "date": "2025-01-15"
       }
   )
   ```

2. **Preserva contexto semántico** — evita cortar a la mitad de una idea.
   Usa `\n\n` como primer separador para respetar párrafos.

3. **Normaliza antes de chunkear**:
   ```python
   import re
   # Quitar espacios múltiples y saltos de línea excesivos
   texto_limpio = re.sub(r'\n{3,}', '\n\n', texto)
   texto_limpio = re.sub(r' {2,}', ' ', texto_limpio)
   ```

4. **Incluye el título o encabezado** en cada chunk cuando sea posible —
   mejora la recuperación porque el chunk tiene más contexto:
   ```python
   # En lugar de: "Se instala con pip install..."
   # Mejor:       "## Instalación\nSe instala con pip install..."
   ```

---

## 3. Pipeline RAG Completo — Mejores prácticas

### Arquitectura recomendada

```
Documentos → Limpieza → Chunking → Embeddings → VectorDB
                                                    ↓
Usuario → Query → Embedding (query) → Búsqueda vectorial → Top-K chunks
                                                                ↓
Usuario ← Respuesta ← LLM ← Prompt con contexto ← Chunks recuperados
```

### Parámetros clave

| Parámetro | Valor típico | Impacto |
|---|---|---|
| `k` (top-K docs) | 3–5 | Más k = más contexto pero más tokens y ruido |
| `chunk_size` | 300–500 tokens | Ver tabla anterior |
| `chunk_overlap` | 10% del chunk | Preserva continuidad |
| `temperature` del LLM | 0–0.3 para RAG | Respuestas más fieles al contexto |

### Errores comunes y cómo evitarlos

**Error 1: Usar el mismo modelo para indexar y consultar con Cohere**
```python
# ❌ Incorrecto — mismo input_type para todo
embeddings = CohereEmbeddings(model="embed-v4.0", input_type="search_document")

# ✅ Correcto — diferenciar entre indexado y consulta
embeddings_index = CohereEmbeddings(model="embed-v4.0", input_type="search_document")
embeddings_query = CohereEmbeddings(model="embed-v4.0", input_type="search_query")
```

**Error 2: k demasiado alto**
```python
# ❌ k=10 mete demasiado ruido al LLM
retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

# ✅ k=3 es el punto dulce para la mayoría de casos
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
```

**Error 3: No limpiar el texto antes de chunkear**
```python
# ❌ Texto con headers HTML, múltiples saltos de línea, etc.
chunks = splitter.split_text(texto_crudo)

# ✅ Limpiar primero
texto_limpio = texto_crudo.replace('\xa0', ' ').strip()
chunks = splitter.split_text(texto_limpio)
```

### Técnicas avanzadas (para cuando necesites más calidad)

#### Hybrid Search (búsqueda híbrida)
Combina búsqueda semántica + keyword search. Muy útil cuando los usuarios
buscan términos técnicos específicos (nombres, códigos, IDs).

```python
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

bm25 = BM25Retriever.from_documents(docs)
semantico = vectorstore.as_retriever()

hybrid = EnsembleRetriever(
    retrievers=[bm25, semantico],
    weights=[0.3, 0.7]  # 70% semántico, 30% keyword
)
```

#### Re-ranking
Después de recuperar los K documentos, usa un modelo de re-ranking para
ordenarlos mejor antes de pasarlos al LLM.

```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain_cohere import CohereRerank

reranker = CohereRerank(model="rerank-v3.5", top_n=3)
retriever_con_rerank = ContextualCompressionRetriever(
    base_compressor=reranker,
    base_retriever=vectorstore.as_retriever(search_kwargs={"k": 10})
)
```

---

## 4. Checklist rápida antes de hacer deploy de un RAG

- [ ] ¿Los chunks tienen tamaño consistente y metadata?
- [ ] ¿Estás usando `input_type` correcto si usas Cohere?
- [ ] ¿`temperature` del LLM es baja (0–0.3) para respuestas fieles?
- [ ] ¿Estás mostrando las fuentes al usuario?
- [ ] ¿Tienes un fallback si no se encuentra información relevante?
- [ ] ¿Evaluaste la calidad con preguntas de prueba?

---

## 5. Recursos

- [Cohere Embeddings Docs](https://docs.cohere.com/docs/embeddings)
- [LangChain RAG How-To](https://python.langchain.com/docs/how_to/#qa-with-rag)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) — ranking actualizado de modelos de embedding
- [ChromaDB Docs](https://docs.trychroma.com/)
