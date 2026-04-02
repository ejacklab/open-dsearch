"""Result deduplication."""

import hashlib
import re
from dataclasses import dataclass
from typing import List, Set, Dict, Optional
from urllib.parse import urlparse

from ..providers.base import SearchResult


@dataclass
class DedupConfig:
    """Deduplication configuration."""
    # URL-based dedup
    normalize_urls: bool = True
    ignore_fragments: bool = True
    ignore_query_params: Optional[List[str]] = None
    
    # Content-based dedup
    content_similarity_threshold: float = 0.5
    min_content_length: int = 20
    
    # Domain limits
    max_per_domain: int = 3
    
    def __post_init__(self):
        if self.ignore_query_params is None:
            self.ignore_query_params = [
                'utm_source', 'utm_medium', 'utm_campaign',
                'ref', 'source', 'fbclid', 'gclid'
            ]


class Deduplicator:
    """Deduplicate search results."""
    
    def __init__(self, config: Optional[DedupConfig] = None):
        """
        Initialize deduplicator.
        
        Args:
            config: Deduplication configuration
        """
        self.config = config or DedupConfig()
    
    def deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Deduplicate results.
        
        Args:
            results: Search results
            
        Returns:
            Deduplicated results
        """
        if not results:
            return []
        
        # Step 1: URL-based deduplication
        results = self._dedup_by_url(results)
        
        # Step 2: Domain limiting
        results = self._limit_by_domain(results)
        
        # Step 3: Content similarity deduplication
        results = self._dedup_by_content(results)
        
        return results
    
    def _dedup_by_url(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicates by normalized URL."""
        seen_urls: Set[str] = set()
        unique_results = []
        
        for result in results:
            normalized = self._normalize_url(result.url)
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                unique_results.append(result)
        
        return unique_results
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        if not self.config.normalize_urls:
            return url.lower()
        
        try:
            parsed = urlparse(url)
            
            # Normalize scheme and netloc
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            
            # Remove www. prefix
            if netloc.startswith('www.'):
                netloc = netloc[4:]
            
            # Normalize path
            path = parsed.path
            if path.endswith('/'):
                path = path[:-1]
            if not path:
                path = '/'
            
            # Handle query parameters
            query = parsed.query
            if self.config.ignore_query_params and query:
                params = []
                for param in query.split('&'):
                    if '=' in param:
                        key = param.split('=')[0]
                        if key not in self.config.ignore_query_params:
                            params.append(param)
                query = '&'.join(sorted(params))  # Sort for consistency
            
            # Remove fragment if configured
            fragment = parsed.fragment
            if self.config.ignore_fragments:
                fragment = ''
            
            # Reconstruct URL
            normalized = f"{scheme}://{netloc}{path}"
            if query:
                normalized += f"?{query}"
            if fragment and not self.config.ignore_fragments:
                normalized += f"#{fragment}"
            
            return normalized.lower()
            
        except Exception:
            return url.lower()
    
    def _limit_by_domain(self, results: List[SearchResult]) -> List[SearchResult]:
        """Limit results per domain."""
        domain_counts: Dict[str, int] = {}
        limited_results = []
        
        for result in results:
            domain = self._extract_domain(result.url)
            count = domain_counts.get(domain, 0)
            
            if count < self.config.max_per_domain:
                domain_counts[domain] = count + 1
                limited_results.append(result)
        
        return limited_results
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return url
    
    def _dedup_by_content(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove near-duplicate content."""
        if len(results) < 2:
            return results
        
        unique_results = [results[0]]
        
        for result in results[1:]:
            is_duplicate = False
            
            for existing in unique_results:
                similarity = self._content_similarity(result, existing)
                if similarity > self.config.content_similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_results.append(result)
        
        return unique_results
    
    def _content_similarity(
        self,
        result1: SearchResult,
        result2: SearchResult
    ) -> float:
        """Calculate content similarity between two results."""
        # Combine title and snippet
        text1 = f"{result1.title} {result1.snippet}".lower()
        text2 = f"{result2.title} {result2.snippet}".lower()
        
        # Skip if too short
        if len(text1) < self.config.min_content_length or \
           len(text2) < self.config.min_content_length:
            return 0.0
        
        # Calculate Jaccard similarity on word sets
        words1 = set(self._tokenize(text1))
        words2 = set(self._tokenize(text2))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Extract alphanumeric words
        words = re.findall(r'\b[a-zA-Z0-9]{3,}\b', text.lower())
        
        # Remove common stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you',
            'all', 'any', 'can', 'had', 'her', 'was', 'one',
            'our', 'out', 'day', 'get', 'has', 'him', 'his',
            'how', 'its', 'may', 'new', 'now', 'old', 'see',
            'two', 'who', 'boy', 'did', 'she', 'use', 'her',
            'way', 'many', 'oil', 'sit', 'set', 'run', 'eat',
            'far', 'sea', 'eye', 'ago', 'off', 'too', 'any',
            'say', 'man', 'try', 'ask', 'end', 'why', 'let',
            'put', 'say', 'she', 'try', 'way', 'own', 'say',
        }
        
        return [w for w in words if w not in stop_words]
    
    def get_duplicate_groups(
        self,
        results: List[SearchResult]
    ) -> List[List[SearchResult]]:
        """
        Group results by duplicates.
        
        Args:
            results: Search results
            
        Returns:
            List of duplicate groups
        """
        groups = []
        remaining = results.copy()
        
        while remaining:
            current = remaining.pop(0)
            group = [current]
            
            # Find all similar results
            to_remove = []
            for i, other in enumerate(remaining):
                similarity = self._content_similarity(current, other)
                if similarity > self.config.content_similarity_threshold:
                    group.append(other)
                    to_remove.append(i)
            
            # Remove found duplicates (in reverse order)
            for i in reversed(to_remove):
                remaining.pop(i)
            
            groups.append(group)
        
        return groups