# Dashboard ClickIT con Integraciones LLM

## Descripcion

Dashboard interno para ClickIT que integra capacidades de LLM para:
- Resumir reportes y metricas automaticamente
- Chat interno con documentacion de la empresa
- Generacion de propuestas y estimaciones
- Analisis de tickets/issues con IA

## Arquitectura

```
┌─────────────────────────────────────────────────┐
│                  Frontend (Next.js)              │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Dashboard │ │ Chat IA  │ │ Reportes Auto    │ │
│  └─────┬────┘ └─────┬────┘ └────────┬─────────┘ │
└────────┼────────────┼───────────────┼────────────┘
         │            │               │
┌────────▼────────────▼───────────────▼────────────┐
│                  API (FastAPI)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ /metrics │ │ /chat    │ │ /reports/generate │  │
│  └─────┬────┘ └─────┬────┘ └────────┬─────────┘  │
└────────┼────────────┼───────────────┼─────────────┘
         │            │               │
   ┌─────▼─────┐ ┌───▼────┐  ┌──────▼──────┐
   │ PostgreSQL │ │ RAG    │  │ LLM Service │
   │ (metricas) │ │ Engine │  │ (Claude/GPT)│
   └───────────┘ └────────┘  └─────────────┘
```

## Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy
- **Frontend**: Next.js 14, Tailwind CSS, shadcn/ui
- **LLM**: Anthropic Claude (principal), OpenAI (fallback)
- **Vector DB**: ChromaDB (para RAG con docs internas)
- **DB**: PostgreSQL
- **Cache**: Redis
- **Auth**: Auth0

## Inicio Rapido

```bash
# 1. Clonar e instalar
git clone <repo>
cd dashboard_poncho
pip install -r requirements.txt

# 2. Configurar environment
cp .env.example .env
# Editar .env con tus keys

# 3. Levantar servicios
docker-compose up -d  # PostgreSQL + Redis

# 4. Correr migraciones
python -m alembic upgrade head

# 5. Iniciar servidor
uvicorn app:app --reload --port 8000
```

## Endpoints Principales

| Endpoint | Metodo | Descripcion |
|----------|--------|-------------|
| `/api/chat` | POST | Chat con IA sobre docs internas |
| `/api/reports/generate` | POST | Genera reporte con resumen IA |
| `/api/metrics/summary` | GET | Metricas con insights automaticos |
| `/api/proposals/draft` | POST | Genera borrador de propuesta |
| `/api/tickets/analyze` | POST | Analiza y clasifica tickets |

## Integraciones LLM Internas

### 1. Chat con Documentacion (RAG)
Permite a cualquier empleado chatear con la documentacion interna de ClickIT:
- Procesos internos
- Guias tecnicas
- Politicas de la empresa

### 2. Resumen Automatico de Metricas
Cada lunes genera un resumen ejecutivo de las metricas clave de la semana anterior, enviado por Slack.

### 3. Generador de Propuestas
A partir de un brief del cliente, genera un borrador de propuesta tecnica con estimacion de tiempo y costo.

### 4. Clasificacion de Tickets
Clasifica automaticamente tickets entrantes por prioridad, area y complejidad estimada.
