#!/usr/bin/env python3
"""
Drift scan — automated harness enforcement for open-dsearch.
Exit 0 = clean. Exit 1 = issues found. Never modifies files.
"""
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
DOCS_DIRS = [ROOT / "docs", ROOT / "rules"]
SRC_PY = list((ROOT / "scripts").glob("*.py"))
SRC_RS = list((ROOT / "scripts" / "rust" / "src").glob("*.rs"))
STALE_DAYS = 30
PY_FN_MAX = 40
RS_FN_MAX = 50

issues: list[str] = []


def check_frontmatter_and_staleness() -> None:
    """Check all docs/rules .md files have YAML frontmatter and are not stale."""
    for docs_dir in DOCS_DIRS:
        if not docs_dir.exists():
            continue
        for md in docs_dir.rglob("*.md"):
            text = md.read_text()
            if not text.startswith("---"):
                issues.append(f"MISSING FRONTMATTER: {md.relative_to(ROOT)}")
                continue
            m = re.search(r"last_verified:\s*(\d{4}-\d{2}-\d{2})", text)
            if not m:
                issues.append(f"MISSING last_verified: {md.relative_to(ROOT)}")
                continue
            verified = date.fromisoformat(m.group(1))
            if date.today() - verified > timedelta(days=STALE_DAYS):
                issues.append(f"STALE ({verified}): {md.relative_to(ROOT)}")


def check_no_secrets() -> None:
    """GP-02: no literal API key values in source files."""
    pattern = re.compile(
        r'(GEMINI_API_KEY|MINIMAX_API_KEY|XAI_API_KEY)\s*=\s*["\'][^"\']{8,}["\']'
    )
    all_src = list((ROOT / "scripts").rglob("*.py")) + list(SRC_RS)
    for f in all_src:
        if pattern.search(f.read_text()):
            issues.append(f"GP-02 SECRETS DETECTED: {f.relative_to(ROOT)}")


def check_python_function_length() -> None:
    """GP-03: Python functions must not exceed 40 lines."""
    fn_re = re.compile(r"^\s*(?:async\s+)?def (\w+)")
    for f in SRC_PY:
        if f.name == "drift_scan.py":
            continue
        lines = f.read_text().splitlines()
        in_fn, fn_start, fn_name, base_indent = False, 0, "", 0
        for i, line in enumerate(lines):
            m = fn_re.match(line)
            if m:
                if in_fn:
                    length = i - fn_start
                    if length > PY_FN_MAX:
                        issues.append(
                            f"GP-03 PY FN TOO LONG ({length} lines) "
                            f"{f.relative_to(ROOT)}:{fn_start + 1} def {fn_name}"
                        )
                in_fn = True
                fn_start = i
                fn_name = m.group(1)
                base_indent = len(line) - len(line.lstrip())
            elif in_fn and line.strip() and not line[0].isspace():
                length = i - fn_start
                if length > PY_FN_MAX:
                    issues.append(
                        f"GP-03 PY FN TOO LONG ({length} lines) "
                        f"{f.relative_to(ROOT)}:{fn_start + 1} def {fn_name}"
                    )
                in_fn = False
        if in_fn:
            length = len(lines) - fn_start
            if length > PY_FN_MAX:
                issues.append(
                    f"GP-03 PY FN TOO LONG ({length} lines) "
                    f"{f.relative_to(ROOT)}:{fn_start + 1} def {fn_name}"
                )


def check_bare_except() -> None:
    """GP-04: no bare except clauses in Python."""
    pattern = re.compile(r"^\s*except\s*:")
    for f in SRC_PY:
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if pattern.match(line):
                issues.append(f"GP-04 BARE EXCEPT: {f.relative_to(ROOT)}:{i}")


def check_hardcoded_paths() -> None:
    """GP-06: no hardcoded absolute /home/* paths in Python scripts."""
    pattern = re.compile(r'["\']\/home\/\w+')
    for f in SRC_PY:
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if pattern.search(line):
                issues.append(f"GP-06 HARDCODED PATH: {f.relative_to(ROOT)}:{i}")


def check_references_unchanged() -> None:
    """GP-07: references/ must not appear in git staged diff."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True, cwd=ROOT
    )
    for changed in result.stdout.splitlines():
        if changed.startswith("references/"):
            issues.append(
                f"GP-07 REFERENCES STAGED: {changed} — needs explicit user approval"
            )


def check_rust_function_length() -> None:
    """GP-03: Rust functions must not exceed 50 lines (brace-depth heuristic)."""
    fn_re = re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn (\w+)")
    for f in SRC_RS:
        lines = f.read_text().splitlines()
        in_fn, fn_start, fn_name, depth = False, 0, "", 0
        for i, line in enumerate(lines):
            m = fn_re.match(line)
            if m and not in_fn:
                in_fn = True
                fn_start = i
                fn_name = m.group(1)
                depth = 0
            if in_fn:
                depth += line.count("{") - line.count("}")
                if depth <= 0 and i > fn_start:
                    length = i - fn_start + 1
                    if length > RS_FN_MAX:
                        issues.append(
                            f"GP-03 RUST FN TOO LONG ({length} lines) "
                            f"{f.relative_to(ROOT)}:{fn_start + 1} fn {fn_name}"
                        )
                    in_fn = False


if __name__ == "__main__":
    check_frontmatter_and_staleness()
    check_no_secrets()
    check_python_function_length()
    check_bare_except()
    check_hardcoded_paths()
    check_references_unchanged()
    check_rust_function_length()

    if issues:
        print(f"drift_scan: {len(issues)} issue(s) found\n")
        for issue in issues:
            print(f"  x {issue}")
        sys.exit(1)
    else:
        print("drift_scan: clean")
        sys.exit(0)
