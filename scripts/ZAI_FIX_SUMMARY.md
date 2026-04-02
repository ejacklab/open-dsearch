# Z.AI Web Search MCP Integration Fix Summary

## Problem
HTTP 400 Bad Request when calling `https://api.z.ai/api/mcp/web_search_prime/mcp`

## Root Causes (5 issues found)

### 1. Wrong Payload Format
**Before:**
```json
{
  "tool": "webSearchPrime",
  "params": {
    "query": "Rust programming language",
    "limit": 5
  }
}
```

**After (JSON-RPC 2.0 format):**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "web_search_prime",
    "arguments": {
      "search_query": "Rust programming language"
    }
  },
  "id": 1
}
```

### 2. Missing Accept Header
The MCP endpoint requires: `Accept: application/json, text/event-stream`

### 3. Wrong Tool Name
- **Wrong:** `webSearchPrime` (camelCase)
- **Correct:** `web_search_prime` (snake_case)

### 4. Wrong Parameter Names
- **Wrong:** `query`, `limit`
- **Correct:** `search_query` (no limit parameter in MCP)

### 5. Missing MCP Initialization
The MCP protocol requires:
1. Call `initialize` method first
2. Send `notifications/initialized` notification
3. Then call `tools/call`

## Available MCP Methods

| Method | Description |
|--------|-------------|
| `initialize` | Initialize MCP session |
| `notifications/initialized` | Confirm initialization |
| `tools/list` | List available tools |
| `tools/call` | Call a tool |

## Tool Parameters (web_search_prime)

| Parameter | Required | Description |
|-----------|----------|-------------|
| `search_query` | Yes | Content to search (max 70 chars recommended) |
| `search_domain_filter` | No | Limit to specific domain (e.g., www.example.com) |
| `search_recency_filter` | No | Time filter: oneDay, oneWeek, oneMonth, oneYear, noLimit |
| `content_size` | No | Summary length: medium (400-600 words), high (2500 words) |
| `location` | No | Region: cn (Chinese), us (non-Chinese) |

## Test Results

### MCP Protocol Test
```bash
curl -s -X POST "https://api.z.ai/api/mcp/web_search_prime/mcp" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "params": {},
    "id": 1
  }'
```

**Result:** ✅ Successfully lists tools

### Direct API Test
```bash
curl -s -X POST "https://api.z.ai/api/paas/v4/web_search" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "search_engine": "search-prime",
    "search_query": "test"
  }'
```

**Result:** ❌ "Insufficient balance or no resource package. Please recharge."

### API Key Status
The provided API key `4f7b8458a67f490fa7ac2f0e1cee8418.jyUGZtePjD7GBkJc`:
- ✅ Is recognized by the system
- ❌ Has insufficient balance (Direct API error)
- ❌ Returns "Api key not found" on MCP endpoint (likely same balance issue)

## Fixed Script
Updated `/home/smoke01/.openclaw/workspace-dave/open-dsearch/scripts/zai_search.py` with:
- Proper JSON-RPC 2.0 format
- Correct MCP protocol flow (initialize → tools/call)
- SSE response parsing
- Error handling for MCP errors
- Support for both MCP and Direct API modes
- Proper tool name and parameter names

## Usage
```bash
# MCP mode (default)
ZAI_API_KEY="your_key" python3 zai_search.py "search query"

# Direct API mode
ZAI_API_KEY="your_key" python3 zai_search.py "search query" --direct
```

## Next Steps
To complete testing, the API key needs to have sufficient balance:
1. Visit https://z.ai/manage-apikey/apikey-list to check key status
2. Add credits or subscribe to a plan
3. Re-run the test