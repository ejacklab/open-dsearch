#!/usr/bin/env python3
"""
Web search wrapper using Rust binaries.
Usage: python web_search.py "query" --limit 10
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def get_rust_binary():
    script_dir = Path(__file__).parent
    binary = script_dir / "rust" / "target" / "release" / "web_search"
    return binary if binary.exists() else None


def search(query: str, limit: int = 10):
    binary = get_rust_binary()
    if not binary:
        print(
            "Error: Rust binary not found. Build with: cd rust && cargo build --release",
            file=sys.stderr,
        )
        return None

    try:
        result = subprocess.run(
            [str(binary), query, "--limit", str(limit)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return {"output": result.stdout, "success": True}
        return {"error": result.stderr, "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


def main():
    parser = argparse.ArgumentParser(
        description="Web search using Rust (MiniMax/Gemini)"
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Number of results")
    parser.add_argument("--output", "-o", help="Output file (JSON)")

    args = parser.parse_args()

    result = search(args.query, args.limit)

    if not result or not result.get("success"):
        print(f"Error: {result.get('error', 'Search failed')}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        with open(args.output, "w") as f:
            f.write(result["output"])
    else:
        print(result["output"])


if __name__ == "__main__":
    main()
