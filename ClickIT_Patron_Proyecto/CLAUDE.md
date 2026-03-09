# CLAUDE.md - Fuente de Verdad del Proyecto ClickIT

> Este archivo es la fuente de verdad para Claude Code y cualquier skill/agente que opere sobre este repositorio.

## Identidad del Proyecto

- **Empresa**: ClickIT (Clicit)
- **Owner**: Poncho (CEO)
- **Stack principal**: Python, FastAPI, LangChain/LangGraph, React/Next.js
- **LLMs en uso**: Claude (Anthropic), GPT-4 (OpenAI), modelos locales via Ollama
- **Infraestructura**: AWS / Vercel / Docker

## Convenciones de Código

### Python
- Formatter: `black` con line-length 100
- Linter: `ruff`
- Type hints obligatorios en funciones públicas
- Docstrings en formato Google style
- Tests con `pytest`

### JavaScript/TypeScript
- Formatter: `prettier`
- Linter: `eslint`
- Framework: Next.js con App Router
- Estilos: Tailwind CSS

### Git
- Commits en inglés, formato conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
- Branch naming: `feature/`, `fix/`, `hotfix/`, `release/`
- PRs requieren al menos 1 review
- Main branch protegido

## Estructura de Proyecto Estándar ClickIT

```
proyecto/
├── CLAUDE.md              # Este archivo - fuente de verdad
├── README.md              # Documentación pública
├── .env.example           # Variables de entorno (sin secrets)
├── .gitignore
├── docker-compose.yml     # Orquestación local
├── Makefile               # Comandos comunes (make dev, make test, etc.)
├── src/
│   ├── api/               # Endpoints FastAPI
│   ├── core/              # Lógica de negocio
│   ├── llm/               # Integraciones con LLMs
│   │   ├── chains.py      # Chains de LangChain
│   │   ├── agents.py      # Agentes configurados
│   │   ├── prompts.py     # Templates de prompts
│   │   └── tools.py       # Tools custom
│   ├── db/                # Modelos y migraciones
│   └── utils/             # Utilidades compartidas
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── frontend/              # Si aplica (Next.js)
├── scripts/               # Scripts de deployment/mantenimiento
└── docs/                  # Documentación técnica extendida
```

## Skills de Claude Disponibles

### /commit
Crea un commit siguiendo conventional commits. Analiza los cambios y genera un mensaje descriptivo.

### /review-pr
Revisa un PR completo: código, tests, seguridad, performance.

### /simplify
Revisa código cambiado buscando oportunidades de simplificación y reutilización.

### /claude-api
Construir aplicaciones con la API de Claude o Anthropic SDK.

### Custom Skills Recomendadas
Para proyectos ClickIT, configurar estas skills adicionales en `.claude/settings.json`:

```json
{
  "skills": {
    "deploy-staging": "Despliega a staging y verifica health checks",
    "db-migrate": "Ejecuta migraciones pendientes con validación",
    "update-docs": "Actualiza documentación basándose en cambios recientes"
  }
}
```

## Reglas para Agentes

1. **Nunca** commitear secrets o API keys
2. **Siempre** correr tests antes de hacer PR
3. **Preferir** editar archivos existentes sobre crear nuevos
4. **Validar** que docker-compose levante correctamente antes de merge
5. Los cambios de infraestructura requieren aprobación explícita de Poncho
6. Para integraciones LLM, siempre incluir fallback y rate limiting
7. Documentar costos estimados de API calls en PRs que toquen LLMs

## Variables de Entorno Requeridas

```
# LLMs
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434

# Base de datos
DATABASE_URL=
REDIS_URL=

# Auth
JWT_SECRET=
AUTH0_DOMAIN=

# Monitoring
LANGSMITH_API_KEY=
SENTRY_DSN=
```

## Contacto y Escalación

- **Decisiones técnicas**: Equipo de desarrollo
- **Decisiones de producto**: Poncho
- **Incidentes**: Canal #incidents en Slack
