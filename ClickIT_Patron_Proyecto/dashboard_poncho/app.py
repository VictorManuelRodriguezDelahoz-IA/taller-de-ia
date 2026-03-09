"""
Dashboard ClickIT - Backend con integraciones LLM
Solucion basica para que Poncho tenga visibilidad de metricas
con capacidades de IA integradas.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

# --- Modelos Pydantic ---

class ChatRequest(BaseModel):
    message: str
    context: str = "general"

class ChatResponse(BaseModel):
    response: str
    sources: list[str] = []
    model: str = ""

class ReportRequest(BaseModel):
    period: str = "weekly"  # weekly, monthly
    areas: list[str] = ["engineering", "sales", "support"]

class ProposalRequest(BaseModel):
    client_name: str
    brief: str
    budget_range: str = ""

class TicketRequest(BaseModel):
    title: str
    description: str


# --- LLM Client ---

class LLMClient:
    """Cliente abstracto para LLMs con fallback automatico."""

    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

    async def complete(self, prompt: str, system: str = "", model: str = "claude") -> dict:
        """Genera una respuesta del LLM con fallback."""
        if model == "claude" and self.anthropic_key:
            return await self._call_anthropic(prompt, system)
        elif self.openai_key:
            return await self._call_openai(prompt, system)
        else:
            return {
                "text": "[Demo Mode] LLM no configurado. Configura ANTHROPIC_API_KEY o OPENAI_API_KEY.",
                "model": "demo",
            }

    async def _call_anthropic(self, prompt: str, system: str) -> dict:
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.anthropic_key)
            message = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system or "Eres un asistente ejecutivo de ClickIT.",
                messages=[{"role": "user", "content": prompt}],
            )
            return {"text": message.content[0].text, "model": "claude-sonnet"}
        except Exception as e:
            # Fallback a OpenAI
            if self.openai_key:
                return await self._call_openai(prompt, system)
            return {"text": f"Error: {e}", "model": "error"}

    async def _call_openai(self, prompt: str, system: str) -> dict:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.openai_key)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system or "Eres un asistente ejecutivo de ClickIT."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1024,
            )
            return {"text": response.choices[0].message.content, "model": "gpt-4o-mini"}
        except Exception as e:
            return {"text": f"Error: {e}", "model": "error"}


# --- App ---

llm = LLMClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Dashboard ClickIT iniciado")
    yield
    print("Dashboard ClickIT detenido")


app = FastAPI(
    title="ClickIT Dashboard API",
    description="Dashboard interno con integraciones LLM para ClickIT",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoints ---

@app.get("/")
async def root():
    return {
        "name": "ClickIT Dashboard API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/metrics/summary")
async def metrics_summary():
    """Devuelve metricas con resumen generado por IA."""
    # En produccion, esto vendria de PostgreSQL
    metrics = {
        "period": "2026-W10",
        "engineering": {
            "prs_merged": 23,
            "bugs_fixed": 8,
            "features_shipped": 3,
            "avg_review_time_hours": 4.2,
        },
        "sales": {
            "leads_generated": 15,
            "proposals_sent": 7,
            "deals_closed": 2,
            "revenue_usd": 45000,
        },
        "support": {
            "tickets_opened": 34,
            "tickets_closed": 31,
            "avg_resolution_hours": 6.5,
            "satisfaction_score": 4.3,
        },
    }

    # Generar insight con IA
    prompt = f"""Analiza estas metricas semanales de ClickIT y genera 3 insights accionables en espanol.
    Se breve y directo (max 3 lineas por insight).

    Metricas: {metrics}"""

    ai_result = await llm.complete(prompt)
    metrics["ai_insights"] = ai_result["text"]
    metrics["ai_model"] = ai_result["model"]

    return metrics


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat con IA sobre documentacion interna."""
    system = """Eres el asistente interno de ClickIT. Respondes preguntas sobre:
    - Procesos internos de la empresa
    - Stack tecnologico (Python, FastAPI, LangChain, AWS)
    - Mejores practicas de desarrollo
    - Politicas de la empresa
    Se conciso y profesional."""

    result = await llm.complete(request.message, system=system)
    return ChatResponse(
        response=result["text"],
        sources=["knowledge_base"],
        model=result["model"],
    )


@app.post("/api/reports/generate")
async def generate_report(request: ReportRequest):
    """Genera un reporte ejecutivo con IA."""
    prompt = f"""Genera un reporte ejecutivo {request.period} para ClickIT.
    Areas a cubrir: {', '.join(request.areas)}

    Formato:
    - Resumen ejecutivo (2-3 oraciones)
    - Highlights por area (bullet points)
    - Recomendaciones (3 max)
    - Riesgos identificados (si hay)

    Escribe en espanol, tono profesional pero accesible para el CEO."""

    result = await llm.complete(prompt)
    return {
        "report": result["text"],
        "generated_at": datetime.now().isoformat(),
        "model": result["model"],
        "period": request.period,
    }


@app.post("/api/proposals/draft")
async def draft_proposal(request: ProposalRequest):
    """Genera borrador de propuesta tecnica."""
    prompt = f"""Genera un borrador de propuesta tecnica para:
    Cliente: {request.client_name}
    Brief: {request.brief}
    Rango de presupuesto: {request.budget_range or 'No especificado'}

    Incluye:
    1. Entendimiento del problema
    2. Solucion propuesta (alto nivel)
    3. Stack tecnologico recomendado
    4. Fases del proyecto
    5. Estimacion de tiempo

    Escribe en espanol, profesional."""

    result = await llm.complete(prompt)
    return {
        "client": request.client_name,
        "draft": result["text"],
        "model": result["model"],
        "generated_at": datetime.now().isoformat(),
        "status": "draft",
    }


@app.post("/api/tickets/analyze")
async def analyze_ticket(request: TicketRequest):
    """Clasifica y analiza un ticket con IA."""
    prompt = f"""Analiza este ticket de soporte/desarrollo:
    Titulo: {request.title}
    Descripcion: {request.description}

    Responde en JSON con:
    - priority: "critical" | "high" | "medium" | "low"
    - area: "engineering" | "support" | "sales" | "infrastructure"
    - complexity: "simple" | "medium" | "complex"
    - suggested_assignee_role: string
    - summary: string (1 oracion)
    - estimated_hours: number"""

    result = await llm.complete(prompt)
    return {
        "ticket_title": request.title,
        "analysis": result["text"],
        "model": result["model"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
