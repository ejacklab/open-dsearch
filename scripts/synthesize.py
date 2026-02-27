#!/usr/bin/env python3
"""
Synthesize research findings into a structured markdown report.
Tries Rust binary first, falls back to Python.
Usage: python synthesize.py --input findings/ --output research.md
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def get_rust_binary():
    script_dir = Path(__file__).parent
    binary = script_dir / "rust" / "target" / "release" / "synthesize"
    return binary if binary.exists() else None


def synthesize_rust(input_dir: str, output: str, title: str):
    binary = get_rust_binary()
    if not binary:
        return None
    
    try:
        result = subprocess.run(
            [str(binary), "--input", input_dir, "--output", output, "--title", title],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        return {"error": result.stderr, "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


def synthesize_python(input_dir: str, output: str, title: str):
    TEMPLATE = """# {title}

## Executive Summary

{summary}

## Technical Architecture

{architecture}

## Key Components

{components}

## Implementation Details

{implementation}

## Sources & Citations

{sources}
"""
    
    findings = []
    path = Path(input_dir)
    if path.exists():
        for f in path.glob("*.md"):
            findings.append(f.read_text())
    
    combined = "\n\n---\n\n".join(findings)
    
    sections = {
        "title": title or "Research Report",
        "summary": "TODO: Write executive summary",
        "architecture": "TODO: Document architecture",
        "components": "TODO: List key components",
        "implementation": "TODO: Describe implementation",
        "sources": "TODO: Add citations"
    }
    
    report = TEMPLATE.format(**sections)
    
    with open(output, "w") as f:
        f.write(report)
    
    return {"success": True, "findings_count": len(findings)}


def synthesize(input_dir: str, output: str, title: str, prefer_rust: bool = True):
    if prefer_rust:
        rust_result = synthesize_rust(input_dir, output, title)
        if rust_result and rust_result.get("success"):
            return {"backend": "rust", "output": rust_result["output"]}
    
    python_result = synthesize_python(input_dir, output, title)
    if python_result:
        return {"backend": "python", "findings_count": python_result.get("findings_count", 0)}
    
    return None


def main():
    parser = argparse.ArgumentParser(description="Synthesize research findings")
    parser.add_argument("--input", "-i", required=True, help="Input directory with findings")
    parser.add_argument("--output", "-o", required=True, help="Output markdown file")
    parser.add_argument("--title", "-t", default="Research Report", help="Report title")
    parser.add_argument("--backend", choices=["rust", "python", "auto"], default="auto", help="Force backend")
    
    args = parser.parse_args()
    
    prefer_rust = args.backend == "auto" or args.backend == "rust"
    result = synthesize(args.input, args.output, args.title, prefer_rust=prefer_rust)
    
    if not result:
        print("Error: Both Rust and Python backends failed", file=sys.stderr)
        sys.exit(1)
    
    print(f"[Using {result['backend']} backend]", file=sys.stderr)
    print(f"Report written to {args.output}")


if __name__ == "__main__":
    main()
