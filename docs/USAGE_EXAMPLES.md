# Open Dsearch - Usage Examples

**Version:** 0.1.0  
**Last Updated:** March 15, 2026

Comprehensive usage examples for all three output modes: vectors, JSON, and markdown.

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Vectors Mode](#vectors-mode)
3. [JSON Mode](#json-mode)
4. [Markdown Mode](#markdown-mode)
5. [Advanced Usage](#advanced-usage)
6. [Integration Examples](#integration-examples)

---

## Quick Reference

### CLI Commands

```bash
# Vectors mode (for RAG/LLM)
python scripts/research.py "topic" --mode vectors

# JSON mode (for programmatic use)
python scripts/research.py "topic" --mode json

# Markdown mode (for human reading)
python scripts/research.py "topic" --mode md
```

### API Calls

```bash
# Vectors
curl -X POST http://localhost:8000/research \
  -d '{"topic": "AI agents", "mode": "vectors"}'

# JSON
curl -X POST http://localhost:8000/research \
  -d '{"topic": "AI agents", "mode": "json"}'

# Markdown
curl -X POST http://localhost:8000/research \
  -d '{"topic": "AI agents", "mode": "md"}'
```

---

## Vectors Mode

Best for: RAG pipelines, LLM context, semantic search, knowledge bases

### Basic Usage

```bash
python scripts/research.py "machine learning vector databases" --mode vectors
```

**What happens:**
1. Searches across 4 providers (Gemini, MiniMax, Kimi, xAI)
2. Generates embeddings for each result
3. Pushes to ZVec vector database
4. Results available for semantic search

### Python Integration

```python
import subprocess
import json

# Research and store vectors
result = subprocess.run(
    ["python", "scripts/research.py", "Rust async patterns", "--mode", "vectors"],
    capture_output=True,
    text=True
)

# Query vectors later (requires zvec)
import zvec

collection = zvec.open("./zvec_data")
results = collection.search(
    vectors={"embedding": get_embedding("How to use async/await?")},
    limit=5
)

for doc in results:
    print(f"{doc.payload['title']}: {doc.payload['url']}")
```

### RAG Pipeline Example

```python
"""
RAG Pipeline with Open Dsearch
"""
import subprocess
import zvec

def research_and_query(topic: str, question: str):
    # Step 1: Research topic and store as vectors
    subprocess.run(
        ["python", "scripts/research.py", topic, "--mode", "vectors", "--top", "20"],
        check=True
    )
    
    # Step 2: Query vectors with specific question
    collection = zvec.open("./zvec_data")
    
    # Get embedding for question (using same model)
    question_embedding = get_embedding(question)
    
    # Search relevant documents
    docs = collection.search(
        vectors={"embedding": question_embedding},
        limit=3
    )
    
    # Step 3: Build context for LLM
    context = "\n\n".join([
        f"Source: {doc.payload['url']}\n{doc.payload['snippet']}"
        for doc in docs
    ])
    
    return context

# Usage
context = research_and_query(
    topic="Kubernetes best practices 2026",
    question="How do I set up resource limits?"
)

# Feed context to your LLM
response = llm.complete(f"Based on this context:\n{context}\n\nAnswer: {question}")
```

### Multi-Topic Knowledge Base

```bash
#!/bin/bash
# build_kb.sh - Build knowledge base from multiple topics

topics=(
    "Rust programming language"
    "Python async patterns"
    "Kubernetes deployment strategies"
    "Docker container optimization"
    "PostgreSQL performance tuning"
)

for topic in "${topics[@]}"; do
    echo "Researching: $topic"
    python scripts/research.py "$topic" --mode vectors --top 15
done

echo "Knowledge base built! Query with zvec."
```

### Vector Mode with Custom Storage

```python
# push_zvec.py usage for custom storage
import subprocess
import json

# Research to JSON first
result = subprocess.run(
    ["python", "scripts/research.py", "topic", "--mode", "json", "--output", "results.json"],
    capture_output=True
)

# Push to zvec manually
with open("results.json") as f:
    results = json.load(f)

for item in results:
    subprocess.run([
        "python", "scripts/push_zvec.py",
        item["title"],
        item["url"],
        item["snippet"],
        "research_topic"
    ])
```

---

## JSON Mode

Best for: Data processing, programmatic analysis, custom formatting, API integration

### Basic Usage

```bash
python scripts/research.py "AI agent frameworks" --mode json --output results.json
```

### Output Format

```json
[
  {
    "title": "AutoGen: Multi-Agent Conversation Framework",
    "url": "https://microsoft.github.io/autogen/",
    "snippet": "AutoGen is a framework for building LLM applications using multiple agents...",
    "source": "gemini",
    "score": 0.95
  },
  {
    "title": "CrewAI - Multi-Agent Systems",
    "url": "https://docs.crewai.com/",
    "snippet": "Framework for orchestrating role-playing AI agents...",
    "source": "minimax",
    "score": 0.92
  }
]
```

### Data Analysis Example

```python
import json
from collections import Counter
from urllib.parse import urlparse

# Load research results
with open("results.json") as f:
    results = json.load(f)

# Analyze by source
sources = Counter([r["source"] for r in results])
print("Results by provider:")
for source, count in sources.items():
    print(f"  {source}: {count}")

# Analyze by domain
domains = Counter([urlparse(r["url"]).netloc for r in results])
print("\nTop domains:")
for domain, count in domains.most_common(5):
    print(f"  {domain}: {count}")

# Filter high-quality results
high_quality = [r for r in results if r["score"] > 0.9]
print(f"\nHigh-quality results (>0.9): {len(high_quality)}")
```

### Custom Report Generation

```python
import json
from datetime import datetime

def generate_custom_report(json_file: str, output_file: str):
    with open(json_file) as f:
        results = json.load(f)
    
    # Group by source
    by_source = {}
    for r in results:
        source = r["source"]
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(r)
    
    # Generate report
    with open(output_file, "w") as f:
        f.write(f"# Research Report\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        
        for source, items in by_source.items():
            f.write(f"## {source.upper()} Results ({len(items)})\n\n")
            for item in sorted(items, key=lambda x: x["score"], reverse=True):
                f.write(f"### {item['title']}\n")
                f.write(f"- URL: {item['url']}\n")
                f.write(f"- Score: {item['score']:.2f}\n")
                f.write(f"- {item['snippet'][:200]}...\n\n")

# Usage
generate_custom_report("results.json", "custom_report.md")
```

### API Integration

```python
import requests
import json

def research_and_process(topic: str) -> dict:
    """Research and return structured data."""
    
    # Call Open Dsearch API
    response = requests.post(
        "http://localhost:8000/research",
        json={"topic": topic, "mode": "json", "top": 10}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data["success"]:
            # Parse JSON output
            results = json.loads(data["output"])
            
            # Process results
            return {
                "topic": topic,
                "total_sources": len(results),
                "providers_used": list(set(r["source"] for r in results)),
                "avg_score": sum(r["score"] for r in results) / len