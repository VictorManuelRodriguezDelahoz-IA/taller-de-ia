"""
Dashboard ClickIT - Backend con integraciones LLM
Para que Poncho vea propuestas, clientes, satisfaccion y metricas de la empresa.
"""

import os
import random
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()


# ============================================================
# DATA DUMMY - En produccion esto viene de PostgreSQL
# ============================================================

CLIENTS = [
    {"id": 1, "name": "Grupo Salinas", "industry": "Retail / Fintech", "contact": "Carlos Mendez", "email": "cmendez@gruposalinas.mx", "status": "active", "since": "2024-03-15", "satisfaction": 4.8, "total_revenue": 185000, "projects_count": 3},
    {"id": 2, "name": "FEMSA Digital", "industry": "Bebidas / Tech", "contact": "Ana Torres", "email": "atorres@femsa.com", "status": "active", "since": "2024-06-01", "satisfaction": 4.5, "total_revenue": 120000, "projects_count": 2},
    {"id": 3, "name": "Kavak", "industry": "Automotive / Marketplace", "contact": "Roberto Luna", "email": "rluna@kavak.com", "status": "active", "since": "2025-01-10", "satisfaction": 4.9, "total_revenue": 95000, "projects_count": 1},
    {"id": 4, "name": "Clip", "industry": "Fintech / Payments", "contact": "Maria Garcia", "email": "mgarcia@clip.mx", "status": "active", "since": "2024-09-20", "satisfaction": 4.2, "total_revenue": 78000, "projects_count": 2},
    {"id": 5, "name": "Bitso", "industry": "Crypto / Fintech", "contact": "Luis Hernandez", "email": "lhernandez@bitso.com", "status": "active", "since": "2025-04-05", "satisfaction": 4.7, "total_revenue": 62000, "projects_count": 1},
    {"id": 6, "name": "Coppel", "industry": "Retail / E-commerce", "contact": "Patricia Solis", "email": "psolis@coppel.com", "status": "churned", "since": "2024-01-15", "satisfaction": 3.1, "total_revenue": 45000, "projects_count": 1},
    {"id": 7, "name": "Rappi MX", "industry": "Delivery / Tech", "contact": "Diego Vargas", "email": "dvargas@rappi.com", "status": "active", "since": "2025-07-12", "satisfaction": 4.6, "total_revenue": 55000, "projects_count": 1},
    {"id": 8, "name": "Konfio", "industry": "Fintech / Lending", "contact": "Sofia Ramirez", "email": "sramirez@konfio.mx", "status": "at_risk", "since": "2024-11-01", "satisfaction": 3.5, "total_revenue": 38000, "projects_count": 1},
    {"id": 9, "name": "Mercado Libre MX", "industry": "E-commerce", "contact": "Jorge Castillo", "email": "jcastillo@mercadolibre.com", "status": "prospect", "since": "2026-01-20", "satisfaction": 0, "total_revenue": 0, "projects_count": 0},
    {"id": 10, "name": "Kueski", "industry": "Fintech / BNPL", "contact": "Fernanda Lopez", "email": "flopez@kueski.com", "status": "prospect", "since": "2026-02-10", "satisfaction": 0, "total_revenue": 0, "projects_count": 0},
]

PROPOSALS = [
    {"id": 1, "client": "Grupo Salinas", "title": "Plataforma RAG para Atencion al Cliente", "amount": 85000, "status": "won", "date": "2025-08-15", "tech": ["RAG", "LangChain", "FastAPI", "AWS"], "description": "Sistema de atencion automatizada con RAG sobre base de conocimiento de 50k documentos."},
    {"id": 2, "client": "FEMSA Digital", "title": "Dashboard BI con Insights de IA", "amount": 65000, "status": "won", "date": "2025-09-01", "tech": ["Claude API", "Next.js", "PostgreSQL"], "description": "Dashboard ejecutivo con generacion automatica de insights semanales via LLM."},
    {"id": 3, "client": "Kavak", "title": "Agente Multi-Modal para Inspeccion Vehicular", "amount": 95000, "status": "won", "date": "2025-11-20", "tech": ["GPT-4 Vision", "LangGraph", "React Native"], "description": "Sistema de inspeccion vehicular con vision por computadora y agentes de validacion."},
    {"id": 4, "client": "Clip", "title": "Chatbot Interno para Onboarding", "amount": 42000, "status": "won", "date": "2025-06-10", "tech": ["Claude API", "ChromaDB", "Slack API"], "description": "Chatbot para automatizar onboarding de nuevos empleados con RAG sobre documentacion interna."},
    {"id": 5, "client": "Clip", "title": "Sistema Anti-Fraude con ML", "amount": 120000, "status": "lost", "date": "2025-10-05", "tech": ["scikit-learn", "FastAPI", "Redis"], "description": "Deteccion de fraude en tiempo real para transacciones. Perdida contra competidor con solucion existente.", "lost_reason": "Competidor con solucion pre-built mas barata"},
    {"id": 6, "client": "Bitso", "title": "Bot de Compliance Regulatorio", "amount": 62000, "status": "won", "date": "2026-01-15", "tech": ["Claude API", "LangGraph", "PostgreSQL"], "description": "Agente que monitorea cambios regulatorios y genera reportes de compliance automaticamente."},
    {"id": 7, "client": "Coppel", "title": "Recomendador de Productos con IA", "amount": 75000, "status": "lost", "date": "2025-04-20", "tech": ["Embeddings", "FastAPI", "Redis"], "description": "Sistema de recomendacion personalizada. Cliente decidio construir internamente.", "lost_reason": "Cliente decidio construir in-house"},
    {"id": 8, "client": "Rappi MX", "title": "Optimizador de Rutas con LLM", "amount": 55000, "status": "won", "date": "2025-12-01", "tech": ["OpenAI", "LangChain", "GraphQL"], "description": "Optimizacion inteligente de rutas de entrega usando LLMs para contexto en tiempo real."},
    {"id": 9, "client": "Konfio", "title": "Analisis de Riesgo Crediticio con IA", "amount": 88000, "status": "in_progress", "date": "2026-02-01", "tech": ["Claude API", "LangGraph", "AWS SageMaker"], "description": "Sistema que analiza solicitudes de credito usando LLMs para extraer y evaluar informacion."},
    {"id": 10, "client": "Mercado Libre MX", "title": "Plataforma de Moderacion de Contenido", "amount": 150000, "status": "pending", "date": "2026-03-01", "tech": ["Claude API", "GPT-4 Vision", "Kafka", "K8s"], "description": "Moderacion automatica de listings usando multimodal AI. Propuesta enviada, esperando respuesta."},
    {"id": 11, "client": "Kueski", "title": "Asistente Virtual para Cobranza", "amount": 70000, "status": "pending", "date": "2026-03-05", "tech": ["Claude API", "Twilio", "FastAPI"], "description": "Agente conversacional para gestion de cobranza empática y personalizada."},
    {"id": 12, "client": "Grupo Salinas", "title": "Expansion RAG - Modulo Legal", "amount": 45000, "status": "in_progress", "date": "2026-02-15", "tech": ["RAG", "LangChain", "Claude API"], "description": "Extension del sistema RAG existente para cubrir documentacion legal y contratos."},
    {"id": 13, "client": "FEMSA Digital", "title": "Pipeline ETL Inteligente", "amount": 55000, "status": "pending", "date": "2026-03-08", "tech": ["LangGraph", "Airflow", "dbt"], "description": "Pipeline de datos con agente IA que detecta anomalias y autocorrige transformaciones."},
]

TEAM = [
    {"name": "Victor Rodriguez", "role": "Lead AI Engineer", "projects": 4, "utilization": 92},
    {"name": "Sofia Chen", "role": "Full Stack Developer", "projects": 3, "utilization": 85},
    {"name": "Miguel Santos", "role": "ML Engineer", "projects": 2, "utilization": 78},
    {"name": "Laura Martinez", "role": "Backend Developer", "projects": 3, "utilization": 88},
    {"name": "Daniel Ochoa", "role": "DevOps Engineer", "projects": 5, "utilization": 95},
    {"name": "Isabella Reyes", "role": "Frontend Developer", "projects": 2, "utilization": 72},
]

MONTHLY_REVENUE = [
    {"month": "2025-04", "revenue": 42000, "costs": 28000},
    {"month": "2025-05", "revenue": 38000, "costs": 26000},
    {"month": "2025-06", "revenue": 55000, "costs": 30000},
    {"month": "2025-07", "revenue": 48000, "costs": 29000},
    {"month": "2025-08", "revenue": 72000, "costs": 35000},
    {"month": "2025-09", "revenue": 65000, "costs": 33000},
    {"month": "2025-10", "revenue": 58000, "costs": 31000},
    {"month": "2025-11", "revenue": 80000, "costs": 38000},
    {"month": "2025-12", "revenue": 75000, "costs": 36000},
    {"month": "2026-01", "revenue": 68000, "costs": 34000},
    {"month": "2026-02", "revenue": 82000, "costs": 40000},
    {"month": "2026-03", "revenue": 45000, "costs": 32000},
]

SATISFACTION_HISTORY = [
    {"month": "2025-04", "score": 4.1, "responses": 12},
    {"month": "2025-05", "score": 4.0, "responses": 15},
    {"month": "2025-06", "score": 4.3, "responses": 18},
    {"month": "2025-07", "score": 4.2, "responses": 14},
    {"month": "2025-08", "score": 4.5, "responses": 20},
    {"month": "2025-09", "score": 4.4, "responses": 16},
    {"month": "2025-10", "score": 4.3, "responses": 19},
    {"month": "2025-11", "score": 4.6, "responses": 22},
    {"month": "2025-12", "score": 4.5, "responses": 17},
    {"month": "2026-01", "score": 4.7, "responses": 21},
    {"month": "2026-02", "score": 4.6, "responses": 24},
    {"month": "2026-03", "score": 4.8, "responses": 10},
]


# ============================================================
# LLM CLIENT
# ============================================================

class LLMClient:
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

    async def complete(self, prompt: str, system: str = "") -> dict:
        if self.anthropic_key:
            return await self._call_anthropic(prompt, system)
        elif self.openai_key:
            return await self._call_openai(prompt, system)
        return {"text": self._demo_response(prompt), "model": "demo"}

    async def _call_anthropic(self, prompt: str, system: str) -> dict:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.anthropic_key)
            message = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system or "Eres un asistente ejecutivo de ClickIT. Responde en espanol.",
                messages=[{"role": "user", "content": prompt}],
            )
            return {"text": message.content[0].text, "model": "claude-sonnet"}
        except Exception:
            if self.openai_key:
                return await self._call_openai(prompt, system)
            return {"text": self._demo_response(prompt), "model": "demo"}

    async def _call_openai(self, prompt: str, system: str) -> dict:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.openai_key)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system or "Eres un asistente ejecutivo de ClickIT. Responde en espanol."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1024,
            )
            return {"text": response.choices[0].message.content, "model": "gpt-4o-mini"}
        except Exception:
            return {"text": self._demo_response(prompt), "model": "demo"}

    def _demo_response(self, prompt: str) -> str:
        responses = [
            "La empresa muestra un crecimiento sostenido del 15% mensual. Las propuestas ganadas superan el 60% del pipeline, lo cual es excelente para el sector tech en LATAM.",
            "Recomiendo priorizar la propuesta de Mercado Libre MX ($150k) - es el deal mas grande en pipeline y podria consolidar nuestra presencia en e-commerce.",
            "El equipo esta a buena capacidad (85% promedio). Sugiero contratar un ML Engineer adicional antes de cerrar la propuesta de Mercado Libre para evitar sobrecargar al equipo.",
            "Los clientes con satisfaccion arriba de 4.5 representan el 70% de nuestros ingresos. El caso de Coppel (3.1) es una leccion: la retencion es mas barata que la adquisicion.",
        ]
        return random.choice(responses)


# ============================================================
# PYDANTIC MODELS
# ============================================================

class ChatRequest(BaseModel):
    message: str

class ProposalCreate(BaseModel):
    client: str
    title: str
    amount: float
    tech: list[str] = []
    description: str = ""


# ============================================================
# FASTAPI APP
# ============================================================

llm = LLMClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n  ClickIT Dashboard corriendo en http://localhost:8000\n")
    yield

app = FastAPI(title="ClickIT Dashboard", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
async def serve_dashboard():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/api/overview")
async def get_overview():
    """KPIs principales para el dashboard."""
    won = [p for p in PROPOSALS if p["status"] == "won"]
    pending = [p for p in PROPOSALS if p["status"] == "pending"]
    in_progress = [p for p in PROPOSALS if p["status"] == "in_progress"]
    lost = [p for p in PROPOSALS if p["status"] == "lost"]
    active_clients = [c for c in CLIENTS if c["status"] == "active"]

    total_revenue = sum(p["amount"] for p in won)
    pipeline_value = sum(p["amount"] for p in pending + in_progress)
    avg_satisfaction = sum(c["satisfaction"] for c in active_clients) / len(active_clients)
    win_rate = len(won) / (len(won) + len(lost)) * 100 if (won or lost) else 0

    return {
        "kpis": {
            "total_revenue": total_revenue,
            "pipeline_value": pipeline_value,
            "active_clients": len(active_clients),
            "avg_satisfaction": round(avg_satisfaction, 1),
            "win_rate": round(win_rate, 1),
            "team_size": len(TEAM),
            "proposals_won": len(won),
            "proposals_pending": len(pending),
            "proposals_in_progress": len(in_progress),
            "proposals_lost": len(lost),
        },
        "monthly_revenue": MONTHLY_REVENUE,
        "satisfaction_history": SATISFACTION_HISTORY,
    }


@app.get("/api/proposals")
async def get_proposals(status: str = "all"):
    """Lista de propuestas, filtrable por status."""
    if status == "all":
        return {"proposals": PROPOSALS, "total": len(PROPOSALS)}
    filtered = [p for p in PROPOSALS if p["status"] == status]
    return {"proposals": filtered, "total": len(filtered)}


@app.get("/api/clients")
async def get_clients(status: str = "all"):
    """Lista de clientes con metricas."""
    if status == "all":
        return {"clients": CLIENTS, "total": len(CLIENTS)}
    filtered = [c for c in CLIENTS if c["status"] == status]
    return {"clients": filtered, "total": len(filtered)}


@app.get("/api/team")
async def get_team():
    """Estado del equipo."""
    avg_util = sum(t["utilization"] for t in TEAM) / len(TEAM)
    return {
        "members": TEAM,
        "avg_utilization": round(avg_util, 1),
        "total": len(TEAM),
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat con IA sobre los datos del dashboard."""
    context = f"""Datos actuales de ClickIT:
- Clientes activos: {len([c for c in CLIENTS if c['status'] == 'active'])}
- Revenue total de propuestas ganadas: ${sum(p['amount'] for p in PROPOSALS if p['status'] == 'won'):,}
- Pipeline (pending + in_progress): ${sum(p['amount'] for p in PROPOSALS if p['status'] in ['pending', 'in_progress']):,}
- Win rate: {len([p for p in PROPOSALS if p['status'] == 'won'])}/{len([p for p in PROPOSALS if p['status'] in ['won', 'lost']])} propuestas
- Satisfaccion promedio clientes activos: {sum(c['satisfaction'] for c in CLIENTS if c['status'] == 'active') / len([c for c in CLIENTS if c['status'] == 'active']):.1f}/5
- Cliente en riesgo: Konfio (3.5/5)
- Cliente perdido: Coppel (3.1/5)
- Propuestas pendientes: {', '.join(p['client'] + ' ($' + str(p['amount']//1000) + 'k)' for p in PROPOSALS if p['status'] == 'pending')}
- Equipo: {len(TEAM)} personas, utilizacion promedio {sum(t['utilization'] for t in TEAM) / len(TEAM):.0f}%

Propuestas detalladas:
""" + "\n".join(f"- {p['title']} ({p['client']}): ${p['amount']:,} - {p['status']}" for p in PROPOSALS)

    system = f"""Eres el asistente ejecutivo de IA de ClickIT. Poncho (el CEO) te esta hablando.
Tienes acceso a los datos de la empresa. Responde de forma concisa, profesional y accionable.
Siempre en espanol. Si te preguntan algo que no sabes, di que no tienes esa informacion.

{context}"""

    result = await llm.complete(request.message, system=system)
    return {"response": result["text"], "model": result["model"]}


@app.get("/api/ai/insights")
async def get_ai_insights():
    """Genera insights con IA sobre el estado actual de la empresa."""
    won = [p for p in PROPOSALS if p["status"] == "won"]
    pending = [p for p in PROPOSALS if p["status"] == "pending"]

    prompt = f"""Como analista de negocios de ClickIT, genera exactamente 4 insights accionables basados en estos datos:

1. Revenue de propuestas ganadas: ${sum(p['amount'] for p in won):,} ({len(won)} propuestas)
2. Pipeline pendiente: ${sum(p['amount'] for p in pending):,} ({len(pending)} propuestas)
3. Cliente en riesgo: Konfio (satisfaccion 3.5/5)
4. Cliente perdido: Coppel (satisfaccion 3.1/5, razon: decidio construir in-house)
5. Win rate: {len(won)}/{len(won) + len([p for p in PROPOSALS if p['status'] == 'lost'])}
6. Propuesta mas grande en pipeline: Mercado Libre MX $150k
7. Equipo al {sum(t['utilization'] for t in TEAM) / len(TEAM):.0f}% de capacidad

Formato: Lista numerada, cada insight en maximo 2 lineas. Incluye accion concreta."""

    result = await llm.complete(prompt)
    return {"insights": result["text"], "model": result["model"], "generated_at": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
