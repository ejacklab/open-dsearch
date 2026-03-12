# REST API Server

## Quick Start

```bash
# Install dependencies
pip install fastapi uvicorn

# Run server
cd scripts
uvicorn api_server:app --reload --port 8000

# Or run directly
python api_server.py
```

## Endpoints

### GET /
Root endpoint with API info

### GET /health
Health check

**Response:**
```json
{
  "status": "healthy",
  "rust_binary": true,
  "python_version": "3.12.3"
}
```

### POST /research
Run deep research

**Request:**
```json
{
  "topic": "AI agents 2026",
  "top": 5,
  "queries": 5,
  "mode": "md",
  "timeout": 300
}
```

**Response:**
```json
{
  "success": true,
  "topic": "AI agents 2026",
  "mode": "md",
  "output": "...markdown report...",
  "time_seconds": 2.8
}
```

### GET /research/sync
Synchronous research (for easy testing)

**Query params:**
- `topic` (required)
- `top` (default: 5)
- `mode` (default: md)

**Example:**
```
GET /research/sync?topic=AI%20agents&top=10&mode=md
```

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Research (POST)
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI agents", "top": 5, "mode": "md"}'

# Research (GET)
curl "http://localhost:8000/research/sync?topic=AI%20agents&top=5"
```

## Interactive Docs

Visit: http://localhost:8000/docs

Swagger UI with full API documentation and testing interface.

## Deployment

### Local
```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

### Production (with Gunicorn)
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api_server:app
```

### Docker
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY scripts/ ./scripts/
COPY requirements-api.txt .

RUN pip install -r requirements-api.txt
RUN apt-get update && apt-get install -y curl && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

WORKDIR /app/scripts
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Environment Variables

```bash
# API keys (required for research)
GEMINI_API_KEY=xxx
MINIMAX_API_KEY=xxx
KIMI_API_KEY=xxx
XAI_API_KEY=xxx
```

## Rate Limiting

Not included in v0.1.0. Add your own:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/research")
@limiter.limit("10/minute")
async def research(request: Request, research_req: ResearchRequest):
    ...
```
