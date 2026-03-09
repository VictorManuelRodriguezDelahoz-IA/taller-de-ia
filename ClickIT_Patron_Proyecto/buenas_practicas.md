# Buenas Practicas ClickIT - Desarrollo con IA

## 1. Arquitectura de Proyectos con LLM

### Principio: Separation of Concerns
Separar la logica de negocio de las integraciones con LLMs. El LLM es un servicio mas, no el centro del sistema.

```
Usuario → API Gateway → Logica de Negocio → LLM Service → Respuesta
                                            ↓
                                      Cache / Fallback
```

### Patron: LLM como Servicio Interno
```python
# src/llm/client.py - Abstraccion del LLM
class LLMClient:
    def __init__(self, provider: str = "anthropic"):
        self.provider = provider
        self.fallback_provider = "openai"

    async def complete(self, prompt: str, **kwargs) -> str:
        try:
            return await self._call_primary(prompt, **kwargs)
        except Exception:
            return await self._call_fallback(prompt, **kwargs)
```

### Patron: Prompt Registry
Centralizar todos los prompts en un solo lugar, versionados y testeables.

```python
# src/llm/prompts.py
PROMPTS = {
    "summarize_v1": "Resume el siguiente texto en 3 puntos clave: {text}",
    "classify_v2": "Clasifica el siguiente ticket en: {categories}\n\nTicket: {ticket}",
    "extract_v1": "Extrae los siguientes campos del documento: {fields}\n\nDocumento: {doc}",
}
```

## 2. Seguridad

### API Keys
- Nunca hardcodear keys en el codigo
- Usar `.env` local + secrets manager en produccion (AWS Secrets Manager, Vault)
- Rotar keys trimestralmente
- Cada desarrollador usa su propia key para desarrollo

### Input Sanitization
- Validar y sanitizar todo input antes de enviarlo al LLM
- Implementar guardrails contra prompt injection
- Limitar longitud de input del usuario

```python
def sanitize_input(user_input: str, max_length: int = 2000) -> str:
    # Truncar
    sanitized = user_input[:max_length]
    # Remover intentos obvios de injection
    danger_patterns = ["ignore previous instructions", "system prompt"]
    for pattern in danger_patterns:
        sanitized = sanitized.replace(pattern, "[filtered]")
    return sanitized
```

### Rate Limiting
- Implementar rate limiting por usuario y por endpoint
- Monitorear costos en tiempo real
- Alertas cuando se supere el 80% del budget mensual

## 3. Performance y Costos

### Caching
- Cache de respuestas identicas (Redis con TTL)
- Cache de embeddings para documentos que no cambian
- Usar modelos mas pequenos para tareas simples

```python
import hashlib
import redis

async def cached_llm_call(prompt: str, ttl: int = 3600) -> str:
    cache_key = hashlib.sha256(prompt.encode()).hexdigest()
    cached = redis.get(cache_key)
    if cached:
        return cached.decode()

    result = await llm_client.complete(prompt)
    redis.setex(cache_key, ttl, result)
    return result
```

### Seleccion de Modelo
| Tarea | Modelo Recomendado | Costo Aprox |
|-------|-------------------|-------------|
| Clasificacion simple | Claude Haiku / GPT-4o-mini | $0.001/req |
| Generacion de texto | Claude Sonnet | $0.01/req |
| Razonamiento complejo | Claude Opus | $0.05/req |
| Embeddings | text-embedding-3-small | $0.0001/req |
| Tareas internas batch | Ollama (local) | $0 |

### Streaming
Para respuestas largas, siempre usar streaming para mejorar UX:

```python
async def stream_response(prompt: str):
    async for chunk in llm_client.stream(prompt):
        yield chunk
```

## 4. Testing de LLMs

### Tests Deterministicos
- Testear la logica alrededor del LLM, no el LLM en si
- Mockear llamadas al LLM en unit tests
- Tests de integracion con LLM real solo en CI/CD (no en cada push)

```python
# tests/unit/test_pipeline.py
def test_prompt_formatting():
    prompt = format_prompt(template="summarize_v1", text="Hello world")
    assert "Hello world" in prompt
    assert "Resume" in prompt

# tests/integration/test_llm.py
@pytest.mark.integration
async def test_llm_responds():
    response = await llm_client.complete("Say 'ok'")
    assert "ok" in response.lower()
```

### Evaluacion de Calidad
- Usar LangSmith para tracing y evaluacion
- Definir metricas: relevancia, precision, latencia
- Mantener un dataset de evaluacion con golden answers

## 5. Observabilidad

### Logging
- Loggear todas las llamadas al LLM (sin el contenido sensible)
- Trackear: latencia, tokens usados, modelo, costo estimado
- Usar structured logging (JSON)

```python
import structlog

logger = structlog.get_logger()

async def call_llm(prompt: str) -> str:
    start = time.time()
    result = await llm_client.complete(prompt)

    logger.info("llm_call",
        model=llm_client.model,
        latency_ms=(time.time() - start) * 1000,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
        estimated_cost=calculate_cost(result.usage),
    )
    return result.text
```

### Dashboards
- Costos diarios/semanales por modelo y endpoint
- Latencia P50, P95, P99
- Error rate por provider
- Top queries mas costosas

## 6. Deployment

### Checklist Pre-Deploy
- [ ] Tests pasan (unit + integration)
- [ ] Variables de entorno configuradas en el ambiente destino
- [ ] Rate limiting configurado
- [ ] Fallback provider configurado
- [ ] Monitoring y alertas activas
- [ ] Costos estimados documentados en el PR
- [ ] Review de seguridad en prompts nuevos

### Ambientes
- **Local**: Ollama para desarrollo rapido y sin costo
- **Staging**: API keys de desarrollo, limites bajos
- **Production**: API keys de produccion, monitoring completo

## 7. Workflow con Claude Code

### Uso Diario
1. Abrir proyecto en VS Code
2. Claude Code ya tiene contexto via `CLAUDE.md`
3. Usar skills: `/commit`, `/review-pr`, `/simplify`
4. Para tareas grandes, usar Plan mode primero

### Mejores Practicas con Claude Code
- Mantener `CLAUDE.md` actualizado como fuente de verdad
- Ser especifico en los prompts: "Agrega endpoint POST /api/users con validacion Pydantic"
- Revisar siempre los cambios antes de aprobar
- Usar agents para tareas complejas que requieren multiples pasos
- No confiar ciegamente: Claude es un copiloto, no autopiloto
