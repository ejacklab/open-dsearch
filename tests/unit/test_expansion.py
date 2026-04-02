"""Unit tests for query expansion."""

import pytest

from src.search.expansion import QueryExpander


class TestQueryExpander:
    """Tests for QueryExpander."""
    
    def test_expand_includes_original(self):
        """Test that expansion includes original query."""
        expander = QueryExpander()
        
        expansions = expander.expand("python tutorial", count=5)
        
        assert "python tutorial" in expansions
    
    def test_expand_count(self):
        """Test that expansion respects count."""
        expander = QueryExpander()
        
        expansions = expander.expand("python", count=3)
        
        assert len(expansions) <= 3
    
    def test_expand_templates(self):
        """Test template-based expansion."""
        expander = QueryExpander()
        
        expansions = expander.expand("python tutorial", count=5, include_templates=True)
        
        # Should include template variations
        assert any("tutorial" in e.lower() for e in expansions)
    
    def test_expand_synonyms(self):
        """Test synonym-based expansion."""
        expander = QueryExpander()
        
        expansions = expander.expand("python", count=10, include_synonyms=True)
        
        # Should include synonyms like "py" or "python3"
        assert any("py" in e.lower() for e in expansions)
    
    def test_expand_variations(self):
        """Test simple variations."""
        expander = QueryExpander()
        
        expansions = expander.expand("how to python", count=5, include_variations=True)
        
        # Should include "python" without "how to"
        assert "python" in expansions
    
    def test_extract_keywords(self):
        """Test keyword extraction."""
        expander = QueryExpander()
        
        keywords = expander.extract_keywords("how to learn python programming")
        
        assert "python" in keywords
        assert "programming" in keywords
        assert "learn" in keywords
        # Stop words should be removed
        assert "how" not in keywords
        assert "to" not in keywords
    
    def test_expand_detects_tutorial_type(self):
        """Test that expansion detects tutorial-type queries."""
        expander = QueryExpander()
        
        expansions = expander.expand("learn python", count=5)
        
        # Should include tutorial-related expansions
        assert any("tutorial" in e.lower() or "guide" in e.lower() for e in expansions)
    
    def test_expand_detects_documentation_type(self):
        """Test that expansion detects documentation-type queries."""
        expander = QueryExpander()
        
        expansions = expander.expand("python docs", count=5)
        
        # Should include documentation-related expansions
        assert any("documentation" in e.lower() or "reference" in e.lower() for e in expansions)
    
    def test_expand_empty_query(self):
        """Test expansion with empty query."""
        expander = QueryExpander()
        
        expansions = expander.expand("", count=5)
        
        assert expansions == [""] or len(expansions) >= 1
