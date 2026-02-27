#!/usr/bin/env python3
"""
Autonomous research pipeline using Rust binaries.
Usage: python research.py "topic" --top 5 --queries 3
       python research.py "topic" --urls "https://..." "https://..."
"""

import argparse
import subprocess
import sys
from pathlib import Path


def get_rust_binary():
    script_dir = Path(__file__).parent
    binary = script_dir / "rust" / "target" / "release" / "research"
    return binary if binary.exists() else None


def research(
    topic: str,
    top: int = 5,
    queries: int = 5,
    urls: list = None,
    output: str = None,
    timeout: int = 300,
    mode: str = "vectors",
):
    binary = get_rust_binary()
    if not binary:
        print(
            "Error: Rust binary not found. Build with: cd rust && cargo build --release",
            file=sys.stderr,
        )
        return None

    cmd = [
        str(binary),
        "--topic",
        topic,
        "--top",
        str(top),
        "--queries",
        str(queries),
        "--timeout",
        str(timeout),
        "--mode",
        mode,
    ]

    if urls:
        for url in urls:
            cmd.extend(["--urls", url])

    if output:
        cmd.extend(["--output", output])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + 30
        )
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        print(f"Error: {result.stderr}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Autonomous research pipeline (Rust)")
    parser.add_argument("topic", help="Research topic")
    parser.add_argument(
        "--top", "-n", type=int, default=5, help="Number of sources to fetch"
    )
    parser.add_argument(
        "--queries", "-q", type=int, default=5, help="Number of search queries"
    )
    parser.add_argument("--urls", "-u", nargs="+", help="Direct URLs (bypasses search)")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument(
        "--timeout", "-t", type=int, default=300, help="Timeout in seconds"
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["vectors", "json", "md"],
        default="vectors",
        help="Output mode",
    )

    args = parser.parse_args()

    result = research(
        args.topic,
        args.top,
        args.queries,
        args.urls,
        args.output,
        args.timeout,
        args.mode,
    )

    if not result:
        print("Error: Research pipeline failed", file=sys.stderr)
        sys.exit(1)

    print(result["output"])


if __name__ == "__main__":
    main()
