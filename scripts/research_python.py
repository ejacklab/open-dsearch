#!/usr/bin/env python3
"""
Pure-Python autonomous research pipeline.
Fallback when Rust binary is unavailable.
"""

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import requests

try:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "push_zvec",
        Path(__file__).parent.resolve() / "push_zvec.py"
    )
    push_zvec = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(push_zvec)
    PUSH_ZVEC_AVAILABLE = True
except Exception as _e:
    import sys as _sys
    print(f"[push_zvec import failed: {_e}]", file=_sys.stderr)
    PUSH_ZVEC_AVAILABLE = False
    push_zvec = None


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str = "unknown"
    score: float = 0.0


@dataclass
class RateLimiter:
    """Token bucket rate limiter."""
    rate: float  # tokens per second
    burst: int   # max bucket size
    _tokens: float = field(default=0.0, init=False)
    _last_update: float = field(default_factory=time.time, init=False)

    def __post_init__(self):
        self._tokens = self.burst

    def acquire(self):
        """Acquire one token. Blocks if necessary."""
        now = time.time()
        elapsed = now - self._last_update
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_update = now

        if self._tokens < 1:
            sleep_time = (1 - self._tokens) / self.rate
            time.sleep(sleep_time)
            self._tokens = 0
        else:
            self._tokens -= 1


# Global rate limiters per provider
_rate_limiters = {
    "gemini": RateLimiter(rate=2.0, burst=5),   # 2 req/sec
    "minimax": RateLimiter(rate=2.0, burst=5),
    "kimi": RateLimiter(rate=1.0, burst=3),
}


def get_secret(provider: str) -> Optional[str]:
    """Get API key from environment or config."""
    try:
        from config import get_secret as config_get_secret
        return config_get_secret(provider)
    except ImportError:
        # Fallback to env only
        env_vars = {
            "gemini": "GEMINI_API_KEY",
            "minimax": "MINIMAX_API_KEY",
            "kimi": "KIMI_API_KEY",
            "xai": "XAI_API_KEY",
        }
        return os.environ.get(env_vars.get(provider, ""))


def validate_topic(topic: str) -> tuple[bool, str]:
    """Validate research topic."""
    if not topic or not topic.strip():
        return False, "Topic cannot be empty"
    if len(topic) > 500:
        return False, "Topic too long (max 500 characters)"
    return True, ""


def expand_queries(topic: str, count: int = 5) -> List[str]:
    """Generate query variations from topic."""
    queries = [topic]
    templates = [
        "{} tutorial",
        "{} guide",
        "{} explained",
        "{} best practices",
        "{} examples",
        "{} documentation",
        "{} github",
        "{} vs alternatives",
    ]
    for i in range(min(count - 1, len(templates))):
        queries.append(templates[i].format(topic))
    return queries[:count]


def with_retry(func, max_retries=3, base_delay=1.0):
    """Decorator for retry with exponential backoff."""
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt)
                print(f"[retry] Attempt {attempt + 1} failed, retrying in {delay:.1f}s: {e}", file=sys.stderr)
                time.sleep(delay)
        return None
    return wrapper


@with_retry
def search_gemini(query: str, limit: int = 10) -> List[SearchResult]:
    """Search using Gemini API with Google Search tool."""
    api_key = get_secret("gemini")
    if not api_key:
        return []

    _rate_limiters["gemini"].acquire()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    body = {
        "contents": [{"role": "user", "parts": [{"text": f"Search for: {query}"}]}],
        "tools": [{"googleSearch": {}}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 1024}
    }

    resp = requests.post(url, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results = []
    candidates = data.get("candidates", [])
    if candidates:
        grounding = candidates[0].get("groundingMetadata", {})
        chunks = grounding.get("groundingChunks", [])
        for chunk in chunks[:limit]:
            web = chunk.get("web", {})
            title = web.get("title", "")
            uri = web.get("uri", "")
            if title and uri:
                results.append(SearchResult(
                    title=title,
                    url=uri,
                    snippet=f"Source for: {query}",
                    source="gemini"
                ))
    return results


@with_retry
def search_minimax(query: str, limit: int = 10) -> List[SearchResult]:
    """Search using MiniMax API."""
    api_key = get_secret("minimax")
    if not api_key:
        return []

    _rate_limiters["minimax"].acquire()

    host = os.environ.get("MINIMAX_API_HOST", "https://api.minimax.io")
    url = f"{host}/v1/coding_plan/search"

    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "MM-API-Source": "dsearch"
        },
        json={"q": query},
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    organic = data.get("organic", [])
    for item in organic[:limit]:
        title = item.get("title", "")
        link = item.get("link", "")
        snippet = item.get("snippet", "")
        if title and link:
            results.append(SearchResult(
                title=title,
                url=link,
                snippet=snippet,
                source="minimax"
            ))
    return results


@with_retry
def search_kimi(query: str, limit: int = 10) -> List[SearchResult]:
    """Search using Kimi (Moonshot AI) API with web_search tool."""
    api_key = get_secret("kimi")
    if not api_key:
        return []

    _rate_limiters["kimi"].acquire()

    host = os.environ.get("KIMI_API_HOST", "https://api.moonshot.ai")
    url = f"{host}/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [
        {"role": "system", "content": f"You are a search assistant. For each result, use the exact format: [title](url) - brief description. Return at most {limit} results."},
        {"role": "user", "content": f"Search the web for: {query}"}
    ]

    # First call triggers the web_search tool
    resp = requests.post(url, headers=headers, json={
        "model": "kimi-k2-turbo-preview",
        "messages": messages,
        "temperature": 0.3,
        "tools": [{"type": "builtin_function", "function": {"name": "$web_search"}}]
    }, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    first_msg = data["choices"][0]["message"]

    # If tool_calls returned (web_search triggered), send tool result back to get actual content
    if first_msg.get("tool_calls"):
        messages.append(first_msg)  # include assistant tool_call message
        tool_call = first_msg["tool_calls"][0]
        # Send back the tool result as required by Moonshot API
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": tool_call["function"].get("arguments", "")
        })

        resp2 = requests.post(url, headers=headers, json={
            "model": "kimi-k2-turbo-preview",
            "messages": messages,
            "temperature": 0.3,
        }, timeout=60)
        resp2.raise_for_status()
        data = resp2.json()

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    results = []

    # Extract [title](url) format
    link_pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'
    for match in re.finditer(link_pattern, content):
        title = match.group(1)
        link = match.group(2)
        # Find description after the link
        after = content[match.end():match.end()+200]
        snippet = after.strip().lstrip('-').strip()[:150]
        results.append(SearchResult(
            title=title,
            url=link,
            snippet=snippet or f"Kimi result for: {query}",
            source="kimi"
        ))

    return results[:limit]


def fetch_url(url: str, max_kb: int = 100) -> dict:
    """Fetch and convert URL to markdown."""
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

        # Simple HTML to text conversion
        text = resp.text
        # Remove scripts and styles
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        # Convert common tags to newlines
        text = re.sub(r'</(p|div|br|h[1-6])>', '\n', text)
        # Remove remaining tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()

        # Truncate to max_kb
        max_chars = max_kb * 1024
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Content truncated]"

        return {
            "url": url,
            "title": resp.headers.get("title", url),
            "markdown": text,
            "byte_size": len(resp.content)
        }
    except Exception as e:
        return {
            "url": url,
            "title": f"Fetch failed: {url}",
            "markdown": f"Error fetching {url}: {e}",
            "byte_size": 0
        }


def verify_urls(results: List[SearchResult], timeout: int = 10, max_workers: int = 20) -> List[SearchResult]:
    """
    Verify that result URLs are reachable (HEAD request with GET fallback).
    Filters out hallucinated or dead links.

    Args:
        results: Search results to verify
        timeout: Per-request timeout in seconds
        max_workers: Parallel workers for verification

    Returns:
        Verified results with a 'verified' field added to metadata
    """
    verified = []
    urls = [r.url for r in results]
    bad_urls = set()

    def check_url(url: str) -> tuple:
        """Check if URL is reachable. Returns (url, status_code or -1)."""
        try:
            resp = requests.head(
                url,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; dsearch/1.0)"},
                allow_redirects=True,
            )
            if resp.status_code < 400:
                return (url, resp.status_code)
            # Some servers don't support HEAD - fallback to GET
            resp2 = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; dsearch/1.0)"},
                allow_redirects=True,
                stream=True,  # don't download body
            )
            resp2.close()
            return (url, resp2.status_code)
        except Exception:
            return (url, -1)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_url, url): url for url in urls}
        for future in as_completed(futures):
            url, status = future.result(timeout=timeout + 5)
            if status < 0 or status >= 400:
                bad_urls.add(url)

    for r in results:
        is_live = r.url not in bad_urls
        if is_live:
            verified.append(r)

    removed = len(results) - len(verified)
    if removed > 0:
        print(f"  ⚠ URL verification: removed {removed} dead/hallucinated links ({len(verified)} verified)")
    else:
        print(f"  ✅ URL verification: all {len(verified)} links verified")

    return verified


def score_and_rank(results: List[SearchResult], top_n: int, query_terms: List[str]) -> List[SearchResult]:
    """Score and rank search results."""
    for r in results:
        score = 0.0
        text = (r.title + " " + r.snippet).lower()

        # Keyword matching
        for kw in query_terms:
            if kw.lower() in text:
                score += 1.0

        # Source quality bonus
        source_scores = {
            "github.com": 2.0,
            "docs.": 1.5,
            "documentation": 1.5,
            "official": 1.0,
        }
        for pattern, bonus in source_scores.items():
            if pattern in r.url.lower():
                score += bonus
                break

        r.score = score

    # Sort by score descending, then dedupe by URL
    seen_urls = set()
    ranked = []
    for r in sorted(results, key=lambda x: x.score, reverse=True):
        if r.url not in seen_urls:
            seen_urls.add(r.url)
            ranked.append(r)

    return ranked[:top_n]


def research(
    topic: str,
    top: int = 5,
    queries: int = 5,
    urls: List[str] = None,
    output: str = None,
    timeout: int = 300,
    mode: str = "vectors",
    verify: bool = False,
    dry_run: bool = False,
    no_fetch: bool = False,
    index: bool = False,
    index_collection: str = None,
) -> Optional[dict]:
    """Run research pipeline."""
    # Validate inputs
    is_valid, error = validate_topic(topic)
    if not is_valid:
        print(f"Error: {error}", file=sys.stderr)
        return None

    if top < 1 or top > 50:
        print("Error: --top must be between 1 and 50", file=sys.stderr)
        return None

    if queries < 1 or queries > 20:
        print("Error: --queries must be between 1 and 20", file=sys.stderr)
        return None

    print(f"🔬 Open Dsearch Research Pipeline")
    print(f"{'=' * 50}")
    print(f"Topic: {topic}\n")

    # Generate queries
    query_list = expand_queries(topic, queries)
    print(f"[dsearch] queries: {query_list}")
    print(f"[dsearch] count: {len(query_list)}\n")

    # Check available providers
    providers = []
    if get_secret("gemini"):
        providers.append("gemini")
    if get_secret("minimax"):
        providers.append("minimax")
    if get_secret("kimi"):
        providers.append("kimi")

    if not providers:
        print("Error: No API keys found. Set GEMINI_API_KEY, MINIMAX_API_KEY, or KIMI_API_KEY.", file=sys.stderr)
        return None

    print(f"[dsearch] providers: {providers}\n")

    # Dry run: show what would be searched without executing
    if dry_run:
        print(f"[dry-run] Would search with {len(query_list)} queries across {providers}")
        for q in query_list:
            print(f"  → {q}")
        if urls:
            print(f"[dry-run] Plus {len(urls)} direct URLs")
        print(f"[dry-run] Mode: {mode}, top: {top}")
        return {"success": True, "dry_run": True}

    # Run searches in parallel
    all_results = []
    keywords = topic.lower().split()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []

        for query in query_list:
            if "gemini" in providers:
                futures.append(executor.submit(search_gemini, query, 10))
            if "minimax" in providers:
                futures.append(executor.submit(search_minimax, query, 10))
            if "kimi" in providers:
                futures.append(executor.submit(search_kimi, query, 10))

        for future in as_completed(futures):
            try:
                results = future.result(timeout=timeout)
                all_results.extend(results)
            except Exception as e:
                print(f"[error] Search failed: {e}", file=sys.stderr)

    # Add direct URLs if provided
    if urls:
        for url in urls:
            all_results.append(SearchResult(
                title=f"User: {url}",
                url=url,
                snippet="User URL",
                source="user"
            ))

    print(f"  Found {len(all_results)} total results")

    # Rank and dedupe
    ranked = score_and_rank(all_results, top_n=top, query_terms=keywords)

    # Verify URLs are reachable (filters hallucinated links)
    if verify:
        ranked = verify_urls(ranked, timeout=10)

    # Push to ZVec if --index flag set
    if index and PUSH_ZVEC_AVAILABLE and not dry_run:
        collection_path = Path(index_collection) if index_collection else None
        count = push_zvec.push_batch(
            [{"title": r.title, "url": r.url, "snippet": r.snippet, "source": r.source} for r in ranked],
            topic,
            collection_path,
        )
        print(f"  → Pushed {count} results to ZVec")
    elif index and not PUSH_ZVEC_AVAILABLE:
        print("  → [zvec] not available (pip install zvec), skipping --index")

    # Output based on mode
    if mode == "json":
        output_data = [
            {"title": r.title, "url": r.url, "snippet": r.snippet, "source": r.source}
            for r in ranked
        ]
        output_file = output or f"{topic.replace(' ', '_')}_raw.json"
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"  ✓ Saved to: {output_file}")
        return {"success": True, "output": json.dumps(output_data)}

    elif mode == "vectors":
        output_data = [{"title": r.title, "url": r.url} for r in ranked]
        output_file = output or f"{topic.replace(' ', '_')}_index.json"
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"  ✓ Index saved to: {output_file}")
        return {"success": True, "output": json.dumps(output_data)}

    else:  # md mode
        output_file = output or f"{topic.replace(' ', '_')}_fetched.md"
        with open(output_file, 'w') as f:
            f.write(f"# Research: {topic}\n\n")

            for i, r in enumerate(ranked, 1):
                if no_fetch:
                    f.write(f"\n## Source {i}: {r.title}\n")
                    f.write(f"**URL:** {r.url}\n\n")
                    f.write(f"_{r.snippet}_\n")
                    print(f"  ✓ (no-fetch) {r.title[:50]}")
                else:
                    page = fetch_url(r.url)
                    f.write(f"\n\n## Source {i}: {page['title']}\n")
                    f.write(f"**URL:** {page['url']}\n\n")
                    f.write(page['markdown'])
                    print(f"  ✓ Fetched: {page['title'][:50]}")

        print(f"  ✓ Report saved to: {output_file}")
        return {"success": True, "output": f"Report saved to {output_file}"}


def main():
    parser = argparse.ArgumentParser(
        description="Open Dsearch - Pure Python Research Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run — see what would be searched without hitting APIs
  python research_python.py "Rust async patterns" --dry-run

  # Fast probe — titles/URLs only, no fetching, no verification
  python research_python.py "Rust async patterns" -m json --top 10

  # Full report with page content (slow — fetches every URL)
  python research_python.py "Rust async patterns" -m md --top 5 --no-fetch
"""
    )
    parser.add_argument("topic", help="Research topic")
    parser.add_argument("--top", "-n", type=int, default=5, help="Number of final sources (after ranking)")
    parser.add_argument("--queries", "-Q", type=int, default=5,
                        help="Number of query variants to generate (1-20)")
    parser.add_argument("--urls", "-u", nargs="+", help="Direct URLs to include (bypasses search)")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--timeout", "-t", type=int, default=300, help="Timeout per provider in seconds")
    parser.add_argument("--mode", "-m", choices=["vectors", "json", "md"], default="vectors",
                        help="vectors=URL index for LLM, json=raw results, md=full report")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show query plan without executing searches")
    parser.add_argument("--no-fetch", action="store_true",
                        help="Skip fetching page content in md mode (titles/URLs/snippets only)")
    parser.add_argument("--verify", action="store_true",
                        help="Verify URLs are reachable before including (slow, marginal value)")
    parser.add_argument("--index", action="store_true",
                        help="Push results to ZVec vector collection after search")
    parser.add_argument("--index-collection", "-C",
                        help="ZVec collection path (default: ~/.open-dsearch/zvec_data)")

    args = parser.parse_args()

    result = research(
        args.topic,
        args.top,
        args.queries,
        args.urls,
        args.output,
        args.timeout,
        args.mode,
        verify=args.verify,
        dry_run=args.dry_run,
        no_fetch=args.no_fetch,
        index=args.index,
        index_collection=args.index_collection,
    )

    if not result:
        sys.exit(1)


if __name__ == "__main__":
    main()
