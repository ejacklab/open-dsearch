#!/usr/bin/env python3
"""
Web fetcher - converts HTML to markdown.
Tries Rust binary first, falls back to Python.
Usage: python web_fetch.py <url>
"""

import argparse
import subprocess
import sys
from pathlib import Path


def get_rust_binary():
    script_dir = Path(__file__).parent
    binary = script_dir / "rust" / "target" / "release" / "web_fetch"
    return binary if binary.exists() else None


def fetch_rust(url: str, max_kb: int = 100):
    binary = get_rust_binary()
    if not binary:
        return None
    
    try:
        result = subprocess.run(
            [str(binary), url, "--max-kb", str(max_kb)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return {"content": result.stdout, "success": True}
        return {"error": result.stderr, "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


def fetch_python(url: str, max_kb: int = 100):
    try:
        import httpx
        from markdownify import markdownify as md
    except ImportError:
        print("Error: Install dependencies: pip install httpx markdownify", file=sys.stderr)
        return None
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"
    }
    
    response = httpx.get(url, headers=headers, timeout=30.0)
    response.raise_for_status()
    
    content = response.text[:max_kb * 1024]
    markdown = md(content, heading_style="ATX")
    
    return {"content": markdown}


def fetch(url: str, max_kb: int = 100, prefer_rust: bool = True):
    if prefer_rust:
        rust_result = fetch_rust(url, max_kb)
        if rust_result and rust_result.get("success"):
            return {"backend": "rust", "content": rust_result["content"]}
    
    python_result = fetch_python(url, max_kb)
    if python_result:
        return {"backend": "python", "content": python_result["content"]}
    
    return None


def main():
    parser = argparse.ArgumentParser(description="Fetch URL and convert to markdown")
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("--max-kb", type=int, default=100, help="Max KB to fetch")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--backend", choices=["rust", "python", "auto"], default="auto", help="Force backend")
    
    args = parser.parse_args()
    
    prefer_rust = args.backend == "auto" or args.backend == "rust"
    result = fetch(args.url, args.max_kb, prefer_rust=prefer_rust)
    
    if not result:
        print("Error: Both Rust and Python backends failed", file=sys.stderr)
        sys.exit(1)
    
    print(f"[Using {result['backend']} backend]", file=sys.stderr)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(result["content"])
    else:
        print(result["content"])


if __name__ == "__main__":
    main()
