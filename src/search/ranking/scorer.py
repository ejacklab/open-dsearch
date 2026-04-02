"""Result scoring and ranking."""

import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from ..providers.base import SearchResult


@dataclass
class ScoringWeights:
    """Weights for scoring factors."""
    keyword_match: float = 1.0
    source_quality: float = 2.0
    title_relevance: float = 1.5
    snippet_quality: float = 0.5
    recency: float = 0.3


class ResultScorer:
    """Score and rank search results."""
    
    # Source quality scores
    SOURCE_SCORES = {
        "github.com": 3.0,
        "docs.": 2.5,
        "documentation": 2.0,
        "reference": 1.8,
        "api.": 1.8,
        "developer.": 1.5,
        "blog.": 0.8,
        "medium.com": 0.7,
        "reddit.com": 0.5,
        "stackoverflow.com": 2.0,
        "stackexchange.com": 1.8,
        "wikipedia.org": 1.2,
        "arxiv.org": 1.5,
        "scholar.google": 1.8,
        "edu": 1.3,
        "gov": 1.3,
    }
    
    def __init__(self, weights: Optional[ScoringWeights] = None):
        """
        Initialize scorer.
        
        Args:
            weights: Scoring weights
        """
        self.weights = weights or ScoringWeights()
    
    def score_results(
        self,
        results: List[SearchResult],
        query: str,
        query_terms: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Score and rank results.
        
        Args:
            results: Search results to score
            query: Original query
            query_terms: Optional pre-tokenized query terms
            
        Returns:
            Results with scores, sorted by score
        """
        if not results:
            return []
        
        # Tokenize query if not provided
        if query_terms is None:
            query_terms = self._tokenize(query)
        
        # Score each result
        for result in results:
            result.score = self._calculate_score(result, query_terms)
        
        # Sort by score descending
        return sorted(results, key=lambda r: r.score, reverse=True)
    
    def _calculate_score(
        self,
        result: SearchResult,
        query_terms: List[str]
    ) -> float:
        """Calculate score for a single result."""
        score = 0.0
        
        text = (result.title + " " + result.snippet).lower()
        url_lower = result.url.lower()
        
        # Keyword matching
        keyword_score = self._score_keywords(text, query_terms)
        score += keyword_score * self.weights.keyword_match
        
        # Source quality
        source_score = self._score_source(url_lower)
        score += source_score * self.weights.source_quality
        
        # Title relevance
        title_score = self._score_title(result.title.lower(), query_terms)
        score += title_score * self.weights.title_relevance
        
        # Snippet quality
        snippet_score = self._score_snippet(result.snippet)
        score += snippet_score * self.weights.snippet_quality
        
        # Recency bonus (if timestamp available)
        if result.timestamp:
            recency_score = self._score_recency(result.timestamp)
            score += recency_score * self.weights.recency
        
        return round(score, 2)
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into search terms."""
        # Remove special chars, split on whitespace
        tokens = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'shall',
            'can', 'need', 'dare', 'ought', 'used',
            'to', 'of', 'in', 'for', 'on', 'with', 'at',
            'by', 'from', 'as', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between',
            'and', 'but', 'or', 'yet', 'so', 'if', 'because',
            'although', 'though', 'while', 'where', 'when',
            'that', 'which', 'who', 'whom', 'whose', 'what',
            'this', 'these', 'those', 'i', 'you', 'he', 'she',
            'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        }
        
        return [t for t in tokens if t not in stop_words]
    
    def _score_keywords(self, text: str, query_terms: List[str]) -> float:
        """Score based on keyword matches."""
        if not query_terms:
            return 0.0
        
        matches = sum(1 for term in query_terms if term in text)
        return matches / len(query_terms)
    
    def _score_source(self, url: str) -> float:
        """Score based on source quality."""
        score = 0.0
        
        for pattern, bonus in self.SOURCE_SCORES.items():
            if pattern in url:
                score = max(score, bonus)
        
        return score
    
    def _score_title(self, title: str, query_terms: List[str]) -> float:
        """Score based on title relevance."""
        if not query_terms:
            return 0.0
        
        matches = sum(1 for term in query_terms if term in title)
        
        # Bonus for exact phrase match
        if len(query_terms) > 1:
            phrase = ' '.join(query_terms)
            if phrase in title:
                matches += 1
        
        return min(matches / len(query_terms) * 1.5, 2.0)
    
    def _score_snippet(self, snippet: str) -> float:
        """Score based on snippet quality."""
        if not snippet:
            return 0.0
        
        score = 0.0
        length = len(snippet)
        
        # Prefer medium-length snippets
        if 100 <= length <= 500:
            score += 1.0
        elif 50 <= length < 100:
            score += 0.5
        elif length > 500:
            score += 0.3
        
        # Penalize very short snippets
        if length < 50:
            score -= 0.5
        
        return score
    
    def _score_recency(self, timestamp) -> float:
        """Score based on recency."""
        from datetime import datetime, timezone
        
        try:
            now = datetime.now(timezone.utc)
            if timestamp.tzinfo is None:
                # Assume UTC if no timezone
                age_days = (now - timestamp.replace(tzinfo=timezone.utc)).days
            else:
                age_days = (now - timestamp).days
            
            # Exponential decay
            import math
            return math.exp(-age_days / 365)  # Half-life of 1 year
        except Exception:
            return 0.0
    
    def get_top_results(
        self,
        results: List[SearchResult],
        n: int = 10,
        min_score: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Get top N results.
        
        Args:
            results: Scored results
            n: Number of results to return
            min_score: Minimum score threshold
            
        Returns:
            Top N results
        """
        if min_score is not None:
            results = [r for r in results if r.score >= min_score]
        
        return results[:n]
    
    def filter_by_domain(
        self,
        results: List[SearchResult],
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Filter results by domain.
        
        Args:
            results: Search results
            allowed_domains: Only include these domains (None = all)
            blocked_domains: Exclude these domains
            
        Returns:
            Filtered results
        """
        filtered = results
        
        if allowed_domains:
            allowed = [d.lower() for d in allowed_domains]
            filtered = [
                r for r in filtered
                if any(d in urlparse(r.url).netloc.lower() for d in allowed)
            ]
        
        if blocked_domains:
            blocked = [d.lower() for d in blocked_domains]
            filtered = [
                r for r in filtered
                if not any(d in urlparse(r.url).netloc.lower() for d in blocked)
            ]
        
        return filtered
