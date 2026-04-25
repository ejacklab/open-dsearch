# Open DSearch

A cutting-edge research platform for AI agents, protocols, and deep research methodologies.

## Overview

Open DSearch combines advanced search capabilities with vector storage and multi-model AI integration for comprehensive research automation. It provides:

- **Multi-Model Search**: Integration with xAI (Grok), Gemini, MiniMax, Brave Search, and Kimi APIs
- **Vector Storage**: ZVec for persistent research data and semantic search
- **Modular Skills**: Claude Code skills for specialized research tasks
- **Rust Performance**: Fast research tools with Python fallbacks
- **Modern Architecture**: MCP (Model Context Protocol) compliant design

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                           │
│         (Claude Code, CLI, Custom Apps)                    │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│                   RESEARCH CORE                             │
│     (Multi-model search, Vector storage, Skills engine)    │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│                 INTEGRATION LAYER                          │
│        (xAI, Gemini, MiniMax APIs, ZVec, MCP)              │
└─────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Clone the repository
git clone https://github.com/ejacklab/open-dsearch.git
cd open-dsearch

# Install dependencies
cargo install --locked

# Initialize configuration
dsearch init
```

## Configuration

Create a `dsearch.toml` file in your project root:

```toml
[models]
  [models.gemini]
  api_key = "your_gemini_api_key"
  model = "gemini-pro"

  [models.xai]
  api_key = "your_xai_api_key"
  model = "grok-beta"

  [models.minimax]
  api_key = "your_minimax_api_key"
  model = "abab6.5-chat"

[storage]
  vector_db_path = "./data/vectors"
  max_memory_mb = 1024

[skills]
  skills_path = "./skills"
  auto_load = true
```

## Usage

### Basic Search

```bash
# Multi-model research search
dsearch "latest developments in quantum computing"

# Target specific models
dsearch --model gemini "climate change impacts"

# Save research session
dsearch --save "quantum-research" "quantum computing trends"
```

### Interactive Research

```bash
# Start interactive session
dsearch interactive

# Load previous session
dsearch load "quantum-research"
```

## Skills

Open DSearch supports modular skills for specialized research tasks:

- **Web Research**: Automated web scraping and analysis
- **Literature Review**: Academic paper search and summarization
- **Data Analysis**: Statistical analysis and visualization
- **Code Review**: Programming language analysis
- **Policy Research**: Government document analysis

## API Integration

### Multi-Model Search API

```python
from dsearch import DSearch

# Initialize with multiple models
ds = DSearch(
    models=["gemini", "xai", "minimax"],
    storage_path="./data/vectors"
)

# Perform multi-model search
results = ds.search(
    query="AI safety research",
    max_results=10,
    models=["gemini", "xai"]
)
```

### Vector Storage Integration

```python
# Store and search research data
ds.store_vector(
    id="paper_001",
    content="Research paper content...",
    metadata={"author": "John Doe", "date": "2024"}
)

# Semantic search
results = ds.semantic_search("similar research on AI safety")
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.