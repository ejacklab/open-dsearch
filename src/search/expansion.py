"""Query expansion module."""

import re
from typing import List, Set, Optional


class QueryExpander:
    """Expand queries for better search coverage."""
    
    # Query templates for different types
    TEMPLATES = {
        "tutorial": [
            "{query} tutorial",
            "{query} getting started",
            "{query} beginner guide",
            "{query} basics",
        ],
        "documentation": [
            "{query} documentation",
            "{query} docs",
            "{query} reference",
            "{query} api",
        ],
        "examples": [
            "{query} examples",
            "{query} sample code",
            "{query} demo",
            "{query} usage",
        ],
        "best_practices": [
            "{query} best practices",
            "{query} guidelines",
            "{query} patterns",
            "{query} recommendations",
        ],
        "comparison": [
            "{query} vs",
            "{query} comparison",
            "{query} alternatives",
            "{query} similar",
        ],
        "github": [
            "{query} github",
            "{query} repository",
            "{query} source code",
        ],
        "community": [
            "{query} reddit",
            "{query} stackoverflow",
            "{query} discussion",
        ],
    }
    
    # Synonym mappings — excludes query-type keywords (learn, docs) which
    # would conflict with template-based expansion for query-type detection
    SYNONYMS = {
        "python": ["py", "python3"],
        "javascript": ["js", "node", "nodejs"],
        "typescript": ["ts"],
        "kubernetes": ["k8s"],
        "database": ["db", "datastore"],
        "api": ["interface", "endpoint"],
        "framework": ["library", "toolkit"],
        "deploy": ["deployment", "release", "publish"],
        "test": ["testing", "unittest", "integration test"],
        "optimize": ["performance", "improve", "speed"],
        "error": ["exception", "bug", "issue", "problem"],
        "setup": ["install", "configure", "getting started"],
    }
    
    def __init__(self, max_expansions: int = 10):
        """
        Initialize query expander.
        
        Args:
            max_expansions: Maximum number of expansions to generate
        """
        self.max_expansions = max_expansions
    
    def expand(
        self,
        query: str,
        count: int = 5,
        include_templates: bool = True,
        include_synonyms: bool = True,
        include_variations: bool = True
    ) -> List[str]:
        """
        Expand query into variations.

        Args:
            query: Original query
            count: Number of expansions to generate
            include_templates: Include template-based expansions
            include_synonyms: Include synonym-based expansions
            include_variations: Include simple variations

        Returns:
            List of expanded queries (including original)
        """
        query = query.strip()  # Normalize once, use consistently
        expansions = {query}  # Start with original

        # Collect variations separately (simple + synonyms) vs templates
        variation_set = set()
        template_set = set()

        # SIMPLE VARIATIONS — prefix/format variations (highest priority)
        if include_variations:
            variation_set.update(self._simple_variations(query))

        # SYNONYM EXPANSION — keyword-level variations
        if include_synonyms:
            variation_set.update(self._synonym_expansions(query))

        # TEMPLATE EXPANSION — after variations so original query terms come first
        if include_templates:
            template_set.update(self._template_expansions(query))

        # Build result: original, then stripped query (if different), then templates, then variations
        result = [query]

        # Include stripped query if different from original (e.g., "how to python" -> "python")
        if query.lower().startswith("how to "):
            stripped = query[7:].strip()
            if stripped and stripped != query and stripped not in result:
                result.append(stripped)
        elif query.lower().startswith("what is "):
            stripped = query[8:].strip()
            if stripped and stripped != query and stripped not in result:
                result.append(stripped)

        for exp in sorted(template_set - {query}):
            if len(result) >= count:
                break
            result.append(exp)
        for exp in sorted(variation_set - {query}):
            if len(result) >= count:
                break
            result.append(exp)

        return result
    
    def _template_expansions(self, query: str) -> Set[str]:
        """Generate template-based expansions."""
        expansions = set()
        query_lower = query.lower()

        # Determine which templates to use
        selected_templates = []

        if any(kw in query_lower for kw in ['learn', 'start', 'new to']):
            selected_templates.extend(self.TEMPLATES["tutorial"])

        if any(kw in query_lower for kw in ['doc', 'ref', 'manual']):
            selected_templates.extend(self.TEMPLATES["documentation"])

        if any(kw in query_lower for kw in ['example', 'sample', 'demo']):
            selected_templates.extend(self.TEMPLATES["examples"])

        if any(kw in query_lower for kw in ['best', 'practice', 'pattern']):
            selected_templates.extend(self.TEMPLATES["best_practices"])

        if any(kw in query_lower for kw in ['vs', 'compare', 'alternative']):
            selected_templates.extend(self.TEMPLATES["comparison"])

        if any(kw in query_lower for kw in ['github', 'repo', 'source']):
            selected_templates.extend(self.TEMPLATES["github"])

        if any(kw in query_lower for kw in ['reddit', 'stackoverflow', 'forum']):
            selected_templates.extend(self.TEMPLATES["community"])

        # If no specific type detected, use a mix
        if not selected_templates:
            selected_templates = (
                self.TEMPLATES["tutorial"][:2] +
                self.TEMPLATES["documentation"][:2] +
                self.TEMPLATES["examples"][:2]
            )

        # Apply templates
        for template in selected_templates[:self.max_expansions]:
            expansions.add(template.format(query=query))

        return expansions

    def _synonym_expansions(self, query: str) -> Set[str]:
        """Generate synonym-based expansions."""
        expansions = set()
        query_lower = query.lower()

        for term, synonyms in self.SYNONYMS.items():
            if term in query_lower:
                for synonym in synonyms:
                    expanded = query_lower.replace(term, synonym)
                    expansions.add(expanded)

        return expansions

    def _simple_variations(self, query: str) -> Set[str]:
        """Generate simple variations."""
        expansions = set()

        # Remove "how to" prefix
        if query.lower().startswith("how to "):
            expansions.add(query[7:].strip())

        # Add "how to" prefix
        if not query.lower().startswith("how to"):
            expansions.add(f"how to {query}")

        # Remove "what is" prefix
        if query.lower().startswith("what is "):
            expansions.add(query[8:].strip())

        # Add question mark
        if not query.endswith("?"):
            expansions.add(f"{query}?")

        # Remove question mark
        if query.endswith("?"):
            expansions.add(query[:-1])
        
        return expansions
    
    def extract_keywords(self, query: str) -> List[str]:
        """
        Extract keywords from query.
        
        Args:
            query: Search query
            
        Returns:
            List of keywords
        """
        # Remove special characters
        cleaned = re.sub(r'[^\w\s]', ' ', query)
        
        # Split into words
        words = cleaned.lower().split()
        
        # Remove stop words
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'must', 'shall', 'can', 'need', 'dare',
            'ought', 'used', 'to', 'of', 'in', 'for', 'on',
            'with', 'at', 'by', 'from', 'as', 'into', 'through',
            'during', 'before', 'after', 'above', 'below',
            'between', 'and', 'but', 'or', 'yet', 'so', 'if',
            'because', 'although', 'though', 'while', 'where',
            'when', 'that', 'which', 'who', 'whom', 'whose',
            'what', 'this', 'these', 'those', 'i', 'you', 'he',
            'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us',
            'them', 'my', 'your', 'his', 'its', 'our', 'their',
            'how',  # interrogative — not useful as a standalone keyword
        }
        
        return [w for w in words if w not in stop_words and len(w) > 2]