# Open Dsearch Troubleshooting Guide

**Version:** 0.1.0  
**Last Updated:** March 15, 2026

Common issues and solutions for Open Dsearch.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [API Key Issues](#api-key-issues)
3. [Rust Binary Issues](#rust-binary-issues)
4. [Search Issues](#search-issues)
5. [Performance Issues](#performance-issues)
6. [Vector Storage Issues](#vector-storage-issues)
7. [API Server Issues](#api-server-issues)
8. [Error Messages](#error-messages)

---

## Installation Issues

### "Rust not found"

**Error:**
```
command not found: cargo
```

**Solution:**
```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Verify
rustc --version
cargo --version
```

### "Python not found"

**Error:**
```
python3: command not found
```

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip

# macOS
brew install python3

# Verify
python3 --version
```

### "Failed to build Rust binary"

**Error:**
```
error: could not compile `research`
```

**Solution:**
```bash
# Clean and rebuild
cd scripts/rust
cargo clean
cargo build --release

# Check for missing dependencies
rustup component add rust-src
```

### "Permission denied"

**Error:**
```
Permission denied: ./research
```

**Solution:**
```bash
# Make binary executable
chmod +x scripts/rust/target/release/research

# Or run with Python
python scripts/research.py "topic"
```

---

## API Key Issues

### "API key not found"

**Error:**
```
Error: GEMINI_API_KEY not set
```

**Solution:**
```bash
# Check if key is set
echo $GEMINI_API_KEY

# Set temporarily
export GEMINI_API_KEY="your-key-here"

# Or add to .env file
echo "GEMINI_API_KEY=your-key-here" > .env
source .env

# Or add to shell profile
echo 'export GEMINI_API_KEY="your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### "Invalid API key"

**Error:**
```
Error: API key invalid or expired
```

**Solution:**
1. Verify key at provider console:
   - Gemini: https://aistudio.google.com/app/apikey
   - MiniMax: https://www.minimax.io
   - Kimi: https://platform.moonshot.cn
   - xAI: https://console.x.ai

2. Check for extra whitespace:
   ```bash
   # Trim whitespace
   export GEMINI_API_KEY=$(echo "$GEMINI_API_KEY" | xargs)
   ```

3. Regenerate key if expired

### "Rate limit exceeded"

**Error:**
```
Error: 429 Too Many Requests
```

**Solution:**
```bash
# Check rate limits
curl "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY"

# Wait and retry
sleep 60

# Use multiple providers to distribute load
python scripts/research.py "topic" --providers gemini,minimax
```

**Rate Limits:**
| Provider | Free Tier | Paid Tier |
|----------|-----------|-----------|
| Gemini | 1000/day | Higher limits |
| MiniMax | N/A | Varies by plan |
| Kimi | N/A | Varies by plan |
| xAI | N/A | Varies by plan |

---

## Rust Binary Issues

### "Rust binary not found"

**Error:**
```
[dsearch] Rust binary not found, using Python fallback...
```

**Solution:**
```bash
# Build Rust binary
cd scripts/rust
cargo build --release

# Verify
cd ../..
python scripts/research.py "test" --mode json
```

**Note:** Python fallback works but is slower (~2.8x).

### "Binary version mismatch"

**Error:**
```
Warning: Rust binary version mismatch
```

**Solution:**
```bash
# Rebuild after updates
cd scripts/rust
cargo clean
cargo build --release
```

### "SIGSEGV (signal 11)"

**Error:**
```
Segmentation fault (core dumped)
```

**Solution:**
```bash
# Rebuild with debug info
cd scripts/rust
cargo build

# Run with debugger
gdb ./target/debug/research
run --topic "test"
bt  # backtrace on crash
```

---

## Search Issues

### "No results found"

**Error:**
```
No results found for query
```

**Solutions:**

1. **Check API keys:**
   ```bash
   env | grep API_KEY
   ```

2. **Try different query:**
   ```bash
   # Too specific
   python scripts/research.py "xyz123abc"  # May fail
   
   # Broader query
   python scripts/research.py "machine learning"  # Better
   ```

3. **Check provider status:**
   ```bash
   curl http://localhost:8000/health
   ```

4. **Increase timeout:**
   ```bash
   python scripts/research.py "topic" --timeout 600
   ```

### "Partial results"

**Issue:** Only some providers return results

**Solution:**
```bash
# Check which providers are working
python scripts/research.py "topic" --mode json

# Results show source for each result
```

**Common causes:**
- Provider rate limits
- Network issues
- API key issues

### "Results are irrelevant"

**Solutions:**

1. **Use more specific queries:**
   ```bash
   # Vague
   python scripts/research.py "AI"
   
   # Specific
   python scripts/research.py "transformer architecture attention mechanism"
   ```

2. **Increase number of queries:**
   ```bash
   python scripts/research.py "topic" --queries 10
   ```

3. **Filter by source:**
   ```bash
   # Use specific providers
   python scripts/research.py "topic" --providers gemini,minimax
   ```

---

## Performance Issues

### "Search is slow"

**Symptoms:** Takes >10 seconds

**Solutions:**

1. **Reduce query count:**
   ```bash
   python scripts/research.py "topic" --queries 3  # Default: 5
   ```

2. **Reduce top results:**
   ```bash
   python scripts/research.py "topic" --top 3  # Default: 5
   ```

3. **Check network:**
   ```bash
   ping google.com
   ```

4. **Use fewer providers:**
   ```bash
   # Use only Gemini
   export MINIMAX_API_KEY=""
   export KIMI_API_KEY=""
   export XAI_API_KEY=""
   ```

5. **Build Rust in release mode:**
   ```bash
   cd scripts/rust
   cargo build --release  # Not just 'cargo build'
   ```

### "High memory usage"

**Symptoms:** System slows down during search

**Solutions:**

1. **Reduce concurrent requests:**
   ```toml
   # ~/.config/dsearch/config.toml
   [search]
   max_concurrent = 10  # Default: 20
   ```

2. **Limit result fetching:**
   ```bash
   python scripts/research.py "topic" --top 5
   ```

3. **Monitor memory:**
   ```bash
   # Linux
   free -h
   
   # macOS
   vm_stat
   ```

---

## Vector Storage Issues

### "zvec not installed"

**Error:**
```
zvec not installed - using file fallback
```

**Solution:**
```bash
# Install zvec (if available)
pip install zvec

# Or use file fallback (JSONL format)
# Results saved to: <topic>_vectors.jsonl
```

### "Vector storage full"

**Error:**
```
Error: No space left on device
```

**Solution:**
```bash
# Check disk space
df -h

# Clean old vectors
rm -rf ./zvec_data/*

# Or use different path
python scripts/research.py "topic" --mode vectors --output /path/with/space
```

### "Embedding failed"

**Error:**
```
Error: Failed to generate embedding
```

**Solution:**
```bash
# Check Gemini API key (used for embeddings)
echo $GEMINI_API_KEY

# Test embedding API
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content": {"parts": [{"text": "test"}]}}'
```

---

## API Server Issues

### "Port already in use"

**Error:**
```
Error: [Errno 98] Address already in use
```

**Solution:**
```bash
# Find and kill process
lsof -i :8000
kill -9 <PID>

# Or use different port
uvicorn api_server:app --port 8001
```

### "CORS error"

**Error:**
```
Access to fetch at 'http://localhost:8000' from origin 'http://localhost:3000' 
has been blocked by CORS policy
```

**Solution:**
```python
# api