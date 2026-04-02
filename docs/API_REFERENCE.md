# Open Dsearch API Reference

**Version:** 0.1.0  
**Last Updated:** March 15, 2026

Complete API reference for Open Dsearch REST API and Python SDK.

---

## Table of Contents

1. [REST API](#rest-api)
2. [Python SDK](#python-sdk)
3. [Data Models](#data-models)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)

---

## REST API

### Base URL

```
http://localhost:8000
```

### Authentication

Currently, the API does not require authentication. Future versions will support API key authentication via the `Authorization: Bearer <token>` header.

### Endpoints

#### GET /

Root endpoint with API information.

**Response:**
```json
{
  "name": "Open Dsearch API",
  "version": "0.1.0",
  "description": "Deep research API - 80+ sources in 2.8s",
  "endpoints": {
    "/research": "POST - Run research query",
    "/health": "GET - Health check",
    "/docs": "GET - API documentation"
  }
}
```

---

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "rust_binary": true,
  "python_version": "3.12.3"
}
```

**Status Values:**
- `healthy` - All systems operational
- `binary_not_found` - Rust binary missing, using Python fallback

---

#### POST /research

Execute deep research on a topic.

**Request Body:**
```json
{
  "topic": "AI agents 2026",
  "top": 5,
  "queries": 5,
  "mode": "md",
  "timeout": 300
}
```

**Parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `topic` | string | Yes | - | Research topic/query |
| `top` | integer | No | 5 | Number of sources to fetch (1-50) |
| `queries` | integer | No | 5 | Number of query variations (1-20) |
| `mode` | string | No | "md" | Output format: `md`, `json`, or `vectors` |
| `timeout` | integer | No | 300 | Timeout in seconds |

**Response (Success):**
```json
{
  "success": true,
  "topic": "AI agents 2026",
  "mode": "md",
  "output": "# Research: AI agents 2026\n\n## Sources...",
  "time_seconds": 2.8
}
```

**Response (Error):**
```json
{
  "success": false,
  "topic": "AI agents 2026",
  "mode": "md",
  "error": "Research failed: API key not found",
  "time_seconds": 0.5
}
```

---

#### GET /research/sync

Synchronous research endpoint for easy testing.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `topic` | string | Yes | - | Research topic |
| `top` | integer | No | 5 | Number of sources |
| `mode` | string | No | "md" | Output format |

**Example:**
```bash
curl "http://localhost:8000/research/sync?topic=AI%20agents&top=10&mode=md"
```

---

## Python SDK

### Installation

```bash
pip install open-dsearch
```

Or install from source:
```bash
git clone https://github.com/ejacklab/open-dsearch.git
cd open-dsearch
pip install -e .
```

### Basic Usage

```python
from dsearch import DSearchClient

# Initialize client
client = DSearchClient()

# Perform research
result = client.research("AI agents 2026")
print(result.output)
```

### Client Configuration

```python
from dsearch import DSearchClient

# Custom endpoint
client = DSearchClient(
    endpoint="http://localhost:8000",
    api_key="optional-api-key",
    timeout=60
)
```

### Methods

#### research(topic, **options)

Execute a research query.

```python
result = client.research(
    topic="machine learning best practices",
    top=10,
    queries=5,
    mode="md",
    timeout=300
)

print(result.success)      # True
print(result.output)       # Markdown report
print(result.time_seconds) # 2.8
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `top` | int | 5 | Number of sources to fetch |
| `queries` | int | 5 | Number of query variations |
| `mode` | str | "md" | Output format: "md", "json", "vectors" |
| `timeout` | int | 300 | Timeout in seconds |

---

#### health()

Check API health status.

```python
health = client.health()
print(health.status)       # "healthy"
print(health.rust_binary)  # True
```

---

## Data Models

### ResearchRequest

```python
class ResearchRequest:
    topic: str           # Research topic
    top: int = 5         # Number of sources
    queries: int = 5     # Query variations
    mode: str = "md"     # Output format
    timeout: int = 300   # Timeout seconds
```

### ResearchResponse

```python
class ResearchResponse:
    success: bool              # Whether research succeeded
    topic: str                 # Original topic
    mode: str                  # Output format used
    output: Optional[str]      # Research output (if success)
    error: Optional[str]       # Error message (if failed)
    time_seconds: Optional[float]  # Execution time
```

### HealthResponse

```python
class HealthResponse:
    status: str        # "healthy" or "binary_not_found"
    rust_binary: bool  # Whether Rust binary is available
    python_version: str
```

### SearchResult (Internal)

```python
@dataclass
class SearchResult:
    title: str      # Result title
    url: str        # Source URL
    snippet: str    # Content snippet
    source: str     # Provider (gemini, minimax, kimi, xai)
    score: float    # Relevance score (0-1)
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid parameters |
| 408 | Request Timeout | Research timed out |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | No providers available |

### Error Response Format

```json
{
  "detail": "Error description"
}
```

### Common Errors

**Rust Binary Not Found:**
```json
{
  "detail": "Rust binary not found. Build with: cd scripts/rust && cargo build --release"
}
```

**Invalid Topic:**
```json
{
  "detail": "Topic cannot be empty"
}
```

**Timeout:**
```json
{
  "detail": "Research timed out after 300 seconds"
}
```

---

## Rate Limiting

### Current Implementation

Rate limiting is implemented per provider using token bucket algorithm:

| Provider | Rate | Burst |
|----------|------|-------|
| Gemini | 2 req/sec | 5 |
| MiniMax | 2 req/sec | 5 |
| Kimi | 1 req/sec | 3 |
| xAI | 2 req/sec | 5 |

### Rate Limit Headers (Future)

Future versions will include rate limit headers:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1700000000
```

### Handling Rate Limits

When rate limited, the API will:
1. Automatically retry with exponential backoff
2. Fall back to available providers
3. Return partial results if some providers succeed

---

## Interactive Documentation

When running the API server, visit:

```
http://localhost:8000/docs
```

For Swagger UI with interactive testing.

---

## Examples

### cURL Examples

**Basic Research:**
```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "Rust async patterns", "top": 10}'
```

**JSON Output:**
```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "vector databases", "mode": "json"}'
```

**Vector Storage:**
```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI agents", "mode": "vectors"}'
```

### Python Examples

**Async Client:**
```python
import asyncio
from dsearch import AsyncDSearchClient

async def main():
    client = AsyncDSearchClient()
    result =