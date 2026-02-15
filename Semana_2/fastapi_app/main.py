"""
FastAPI Application with LangChain Integration
==============================================

Esta aplicación demuestra cómo integrar LangChain con FastAPI
para crear una API de IA lista para producción.

Endpoints:
    - POST /chat: Enviar mensaje al chatbot
    - POST /rag/query: Consultar sistema RAG
    - GET /health: Health check

"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# Cargar variables de entorno
load_dotenv()

# Inicializar FastAPI
app = FastAPI(
    title="AI Workshop API",
    description="API de ejemplo para el Taller de IA",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar LLM
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    api_key=os.getenv("OPENAI_API_KEY")
)


# Modelos Pydantic
class ChatRequest(BaseModel):
    """Modelo para requests de chat."""
    message: str
    system_prompt: Optional[str] = "Eres un asistente útil y amigable."
    temperature: Optional[float] = 0.7


class ChatResponse(BaseModel):
    """Modelo para responses de chat."""
    response: str
    model: str
    tokens_used: Optional[int] = None


class RAGQuery(BaseModel):
    """Modelo para queries RAG."""
    query: str
    top_k: Optional[int] = 3


class RAGResponse(BaseModel):
    """Modelo para responses RAG."""
    answer: str
    sources: List[str]
    confidence: Optional[float] = None


# Endpoints
@app.get("/")
async def root():
    """Endpoint raíz."""
    return {
        "message": "Bienvenido al API del Taller de IA",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat",
            "rag": "/rag/query",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "llm_configured": bool(os.getenv("OPENAI_API_KEY"))
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint de chat simple.
    
    Args:
        request: ChatRequest con mensaje y configuración
        
    Returns:
        ChatResponse con la respuesta del LLM
    """
    try:
        # Crear mensajes
        messages = [
            SystemMessage(content=request.system_prompt),
            HumanMessage(content=request.message)
        ]
        
        # Llamar al LLM
        response = llm.invoke(messages)
        
        return ChatResponse(
            response=response.content,
            model="gpt-4"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/query", response_model=RAGResponse)
async def rag_query(query: RAGQuery):
    """
    Endpoint RAG (placeholder - implementar en Clase 2).
    
    Args:
        query: RAGQuery con la consulta
        
    Returns:
        RAGResponse con respuesta y fuentes
    """
    # TODO: Implementar RAG real en Semana 1, Clase 2
    return RAGResponse(
        answer="Este endpoint será implementado en la Clase 2 de RAG.",
        sources=["placeholder.txt"],
        confidence=0.0
    )


# Endpoint de ejemplo con streaming (avanzado)
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Endpoint de chat con streaming (ejemplo avanzado).
    
    Nota: Requiere configuración adicional para SSE.
    """
    # TODO: Implementar streaming
    raise HTTPException(
        status_code=501,
        detail="Streaming no implementado aún. Ver documentación de LangChain streaming."
    )


# Manejo de errores global
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Manejador global de excepciones."""
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "type": type(exc).__name__
    }


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Iniciando servidor FastAPI...")
    print("📖 Documentación disponible en: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
