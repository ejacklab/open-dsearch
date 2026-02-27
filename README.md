# Open CCLL - Comprehensive Continuous Learning Loop

A cutting-edge research platform for AI agents, protocols, and deep research methodologies. This repository combines advanced search capabilities with vector storage and multi-model AI integration for comprehensive research automation.

## 🚀 Overview

Open CCLL is a comprehensive research framework that integrates multiple AI models (xAI, Gemini, MiniMax) with vector storage for advanced research capabilities. It provides:

- **Multi-Model Search**: Integration with xAI (Grok), Gemini, and MiniMax APIs
- **Vector Storage**: ZVec for persistent research data and semantic search
- **Modular Skills**: Claude Code skills for specialized research tasks
- **Rust Performance**: Fast research tools with Python fallbacks
- **Modern Architecture**: MCP (Model Context Protocol) compliant design

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Skills](#-skills)
- [Research Tools](#-research-tools)
- [API Integration](#-api-integration)
- [Contributing](#-contributing)
- [License](#-license)

## 🏗️ Architecture

The system follows a multi-tier architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                         │
│  (Claude Code, CLI, Custom Apps)                          │
└─────────────────┬─────────────────────────────────────────┘
                  │
┌─────────────────▼─────────────────────────────────────────┐
│                   SKILLS LAYER                            │
│  (dsearch, llms-rust-dev, software-modularity, zvec-rag) │
└─────────────────┬─────────────────────────────────────────┘
                  │
┌─────────────────▼─────────────────────────────────────────┐
│                 RESEARCH ENGINE                           │
│  • Query splitting & optimization                         │
│  • Multi-model orchestration                              │
│  • Result aggregation                                     │
└─────────────────┬─────────────────────────────────────────┘
                  │
┌─────────────────┼─────────────────────────────────────────┐
│  SEARCH APIs    │            VECTOR STORAGE              │
│  • xAI (Grok)  │            • ZVec                      │
│  • Gemini      │            • Semantic search           │
│  • MiniMax     │            • Persistent storage        │
└─────────────────┼─────────────────────────────────────────┘
                  │
┌─────────────────▼─────────────────────────────────────────┐
│                   CORE TOOLS                              │
│  • Rust research tool                                    │
│  • Web fetch & parsing                                   │
│  • Performance benchmarking                              │
└───────────────────────────────────────────────────────────┘
```

## 🛠️ Installation

### Prerequisites

- Rust (latest stable)
- Python 3.8+
- Cargo
- Git

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/ejacklab/open-dsearch.git
cd open-dsearch

# Install Rust components
rustup component add rust-src rustfmt clippy

# Build the research tool
cd research-tool
cargo build --release
cd ..

# Install Python dependencies (if any)
pip install -r requirements.txt  # if exists
```

## ⚙️ Configuration

### API Keys

Set up environment variables for API access:

```bash
# xAI (Grok) API - for real-time web and social platform search
export XAI_API_KEY="your-xai-api-key"

# Gemini API - for comprehensive web search
export GEMINI_API_KEY="your-gemini-api-key"

# MiniMax API - for coding-focused search
export MINIMAX_API_KEY="your-minimax-api-key"

# Additional search engines
export TAVILY_API_KEY="your-tavily-api-key"    # AI-native search
export EXA_API_KEY="your-exa-api-key"          # Semantic search
export BRAVE_API_KEY="your-brave-api-key"      # Privacy-focused search
```

### Environment Setup

```bash
# For development
export RUST_LOG=info
export DEBUG_MODE=true

# For production
export RUST_LOG=warn
export DEBUG_MODE=false
```

## 🎯 Usage

### 1. Basic Research Command

```bash
# Navigate to the research script directory
cd .agents/skills/dsearch/scripts/

# Perform research with vector storage
python research.py "AI agent architectures 2026" --mode vectors

# Save raw JSON results
python research.py "machine learning vector databases" --mode json

# Generate full markdown report
python research.py "Rust async patterns" --mode md --top 10
```

### 2. Using Claude Code Skills

The repository includes several Claude Code skills:

#### dsearch Skill
For comprehensive research using multiple AI models:
- Automatically splits queries into sub-queries
- Uses industry-standard terminology
- Integrates with zvec for vector storage

#### llms-rust-dev Skill
For Rust development best practices:
```bash
# Generate code review
python3 .agents/skills/llms-rust-dev/skill.py research-tool/src/main.rs

# Specify output file
python3 .agents/skills/llms-rust-dev/skill.py research-tool/src/main.rs review.md
```

### 3. Research Tool Usage

```bash
# Run the Rust research tool
cd research-tool
cargo run

# Or run the release version
./target/release/research-tool
```

## 🧩 Skills

### dsearch
**Location:** `.agents/skills/dsearch/`

Comprehensive research methodology using Gemini, MiniMax, or xAI (Grok) search with zvec vector storage.

**Features:**
- Multi-model query execution (20 queries per model)
- Vector storage integration
- Automatic query splitting
- Industry terminology recognition

### llms-rust-dev
**Location:** `.agents/skills/llms-rust-dev/`

Rust development best practices skill with comprehensive code analysis.

**Features:**
- Code review generation
- Best practices analysis (ownership, error handling, concurrency)
- Anti-pattern detection
- Performance optimization suggestions

### software-modularity
**Location:** `.agents/skills/software-modularity/`

Software architecture and modularity analysis.

### zvec-rag
**Location:** `.agents/skills/zvec-rag/`

Vector database and RAG (Retrieval-Augmented Generation) integration.

## 🛠️ Research Tools

### Rust Research Tool
**Location:** `research-tool/`

A high-performance research tool built in Rust that:
- Scopes research topics
- Executes searches across multiple engines (Tavily, Exa, Brave, Grok)
- Benchmarks performance across different search methods
- Generates detailed markdown reports

**Key Features:**
- Modern search stack with AI-native APIs
- xAI Grok integration
- Multi-engine execution
- Performance logging
- Markdown output

### Benchmark Results
The Rust implementation is significantly faster than Python:
- **Rust**: ~0.13s average
- **Python**: ~0.37s average
- **Performance gain**: ~2.8x faster

## 🌐 API Integration

### xAI (Grok) Integration
- **Web Search**: Real-time web search using xAI's Grok model
- **X Platform Search**: Social platform search for real-time discussions
- **Model**: grok-4-1-fast-reasoning
- **Concurrent Queries**: 20 per search phase

### Gemini Integration
- **Comprehensive Search**: Detailed analysis and reasoning
- **API Optimization**: AI-native search capabilities
- **Citation Support**: Proper attribution of sources

### MiniMax Integration
- **Coding Focus**: Specialized for technical and coding queries
- **Specialized Models**: Optimized for programming tasks
- **Code Understanding**: Enhanced for technical documentation

## 📚 Documentation

### Research References
**Location:** `ref/`

Contains comprehensive research findings on:
- Claude's multi-agent research architecture
- MCP (Model Context Protocol) implementation
- Chat.Qwen agentic workflows
- LLM search tools comparison
- Best LLMs for coding tasks

### Architecture Documents
- **AGENTS.md**: Agent workflow and conduct rules
- **XAI_INTEGRATION_EXPLORATION_SUMMARY.md**: Detailed xAI integration documentation
- **research_rust_llms.md**: Rust development best practices
- **CLAUDE.md**: Claude Code guidance and best practices

## 🤝 Contributing

### Development Guidelines

1. **Pre-Execution Planning**: Always research and create a todo list before starting work
2. **Public/Private Boundary**: Respect the boundary between public and private repositories
3. **5W Commit Messages**: Use the 5W framework for commit messages
4. **Senior Developer Standards**: Apply senior-level engineering judgment

### Code Standards

- Write comments that explain *why*, not *what*
- Use structured tags for known issues (`# BUG:`, `# TODO:`, `# HACK:`)
- Follow Rust best practices for ownership and borrowing
- Implement proper error handling with Result types
- Use async patterns appropriately

### Branch Strategy

- Keep the `main` branch stable
- Create feature branches for new functionality
- Use descriptive branch names
- Follow the 5W commit message convention

## 🔒 Security

### API Key Management
- Store API keys in environment variables
- Never commit API keys to the repository
- Use masked values in documentation (e.g., `sk-xxxxxxxxxxx`)
- Regularly rotate API keys

### Data Privacy
- Respect public/private repository boundaries
- Never copy private data to public repositories
- Use proper access controls for sensitive data
- Follow GDPR and other privacy regulations

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support, please:
1. Check the documentation in the `ref/` directory
2. Review the agent conduct rules in `AGENTS.md`
3. Look at the skill documentation in `.agents/skills/`
4. Create an issue in the GitHub repository

---

**Note**: This repository is part of a two-repo workspace structure with separate public and private components. Always ensure you're working in the correct repository and respecting the public/private boundary.

**Last Updated**: February 2026