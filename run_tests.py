#!/usr/bin/env python3
"""Simple test runner for Open Dsearch."""

import sys
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import test modules
from tests.unit.test_providers import (
    TestSearchResult, TestProviderConfig, TestProviderHealth,
    TestProviderRegistry, TestGeminiProvider, TestMiniMaxProvider, TestKimiProvider
)
from tests.unit.test_caching import TestCacheKey, TestMemoryCache, TestSQLiteCache
from tests.unit.test_ranking import TestResultScorer, TestDeduplicator
from tests.unit.test_orchestrator import TestSearchOptions, TestSearchResponse, TestSearchOrchestrator
from tests.unit.test_expansion import TestQueryExpander


def run_test_method(test_class, method_name):
    """Run a single test method."""
    instance = test_class()
    method = getattr(instance, method_name)
    try:
        method()
        return True, None
    except Exception as e:
        return False, str(e)


def run_async_test_method(test_class, method_name):
    """Run an async test method."""
    import asyncio
    instance = test_class()
    method = getattr(instance, method_name)
    try:
        asyncio.run(method())
        return True, None
    except Exception as e:
        return False, str(e)


def run_tests():
    """Run all tests."""
    test_classes = [
        # Provider tests
        (TestSearchResult, "SearchResult", False),
        (TestProviderConfig, "ProviderConfig", False),
        (TestProviderHealth, "ProviderHealth", False),
        (TestProviderRegistry, "ProviderRegistry", False),
        (TestGeminiProvider, "GeminiProvider", False),
        (TestMiniMaxProvider, "MiniMaxProvider", False),
        (TestKimiProvider, "KimiProvider", False),
        
        # Caching tests
        (TestCacheKey, "CacheKey", False),
        (TestMemoryCache, "MemoryCache", True),
        (TestSQLiteCache, "SQLiteCache", True),
        
        # Ranking tests
        (TestResultScorer, "ResultScorer", False),
        (TestDeduplicator, "Deduplicator", False),
        
        # Orchestrator tests
        (TestSearchOptions, "SearchOptions", False),
        (TestSearchResponse, "SearchResponse", False),
        (TestSearchOrchestrator, "SearchOrchestrator", True),
        
        # Expansion tests
        (TestQueryExpander, "QueryExpander", False),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    print("=" * 70)
    print("Open Dsearch Test Suite")
    print("=" * 70)
    print()
    
    for test_class, name, is_async in test_classes:
        print(f"\n{name}:")
        print("-" * 40)
        
        # Get test methods
        methods = [m for m in dir(test_class) if m.startswith("test_")]
        
        for method in methods:
            if is_async:
                success, error = run_async_test_method(test_class, method)
            else:
                success, error = run_test_method(test_class, method)
            
            if success:
                print(f"  ✓ {method}")
                passed += 1
            else:
                print(f"  ✗ {method}")
                print(f"    Error: {error}")
                failed += 1
                errors.append((name, method, error))
    
    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if errors:
        print("\nErrors:")
        for class_name, method_name, error in errors:
            print(f"  {class_name}.{method_name}: {error}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
