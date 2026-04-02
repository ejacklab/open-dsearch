#!/usr/bin/env python3
"""
Test runner script for open-dsearch.
Usage: python run_tests.py [unit|integration|all|live|benchmark]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, description: str) -> int:
    """Run a command and print status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print(f"✅ {description} passed!")
    else:
        print(f"❌ {description} failed!")
    
    return result.returncode


def run_unit_tests() -> int:
    """Run unit tests."""
    return run_command(
        ["pytest", "tests/unit", "-v", "--cov=scripts", "--cov-report=term-missing"],
        "Unit Tests"
    )


def run_integration_tests() -> int:
    """Run integration tests."""
    return run_command(
        ["pytest", "tests/integration", "-v", "-m", "not live_api"],
        "Integration Tests"
    )


def run_live_tests() -> int:
    """Run live API tests."""
    print("\n⚠️  Live API tests require valid API keys in environment!")
    return run_command(
        ["pytest", "tests/integration", "-v", "-m", "live_api"],
        "Live API Tests"
    )


def run_benchmarks() -> int:
    """Run performance benchmarks."""
    return run_command(
        ["pytest", "tests/benchmarks", "-v", "--benchmark-only"],
        "Performance Benchmarks"
    )


def run_all_tests() -> int:
    """Run all tests."""
    results = []
    
    results.append(run_unit_tests())
    results.append(run_integration_tests())
    
    return max(results)


def main():
    parser = argparse.ArgumentParser(
        description="Run open-dsearch tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py unit          # Run unit tests only
  python run_tests.py integration   # Run integration tests
  python run_tests.py all           # Run all tests
  python run_tests.py live          # Run tests with live APIs
  python run_tests.py benchmark     # Run performance benchmarks
        """
    )
    
    parser.add_argument(
        "type",
        choices=["unit", "integration", "all", "live", "benchmark"],
        default="unit",
        nargs="?",
        help="Type of tests to run (default: unit)"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print(f"Open Dsearch Test Runner")
    print(f"Working directory: {os.getcwd()}")
    
    # Run tests based on type
    test_runners = {
        "unit": run_unit_tests,
        "integration": run_integration_tests,
        "all": run_all_tests,
        "live": run_live_tests,
        "benchmark": run_benchmarks,
    }
    
    exit_code = test_runners[args.type]()
    
    print(f"\n{'='*60}")
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ Tests failed with exit code {exit_code}")
    print('='*60)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
