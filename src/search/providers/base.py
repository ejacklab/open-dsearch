"""Abstract base class for search providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class ProviderStatus(Enum):
    """Provider health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    RATE_LIMITED = "rate_limited"


@dataclass
class SearchResult:
    """Standardized search result across all providers."""
    title: str
    url: str
    snippet: str
    source: str
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    fetched_content: Optional[str] = None
    timestamp: Optional[datetime] = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Ensure timestamp is set."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "score": self.score,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        """Create from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                timestamp = datetime.now()
        
        return cls(
            title=data["title"],
            url=data["url"],
            snippet=data["snippet"],
            source=data.get("source", "unknown"),
            score=data.get("score", 0.0),
            metadata=data.get("metadata", {}),
            timestamp=timestamp,
        )


@dataclass
class ProviderConfig:
    """Configuration for a search provider."""
    api_key: str
    timeout_seconds: float = 30.0
    max_retries: int = 3
    rate_limit_per_minute: int = 60
    enabled: bool = True
    priority: int = 1
    extra_headers: Optional[Dict[str, str]] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.0
    
    def __post_init__(self):
        """Initialize extra headers if None."""
        if self.extra_headers is None:
            self.extra_headers = {}


@dataclass
class ProviderHealth:
    """Provider health tracking."""
    status: ProviderStatus = ProviderStatus.HEALTHY
    consecutive_failures: int = 0
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    avg_latency_ms: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0


class SearchProvider(ABC):
    """Abstract base class for search providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self._health = ProviderHealth()
        self._circuit_open = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
    
    @property
    @abstractmethod
    def supports_realtime(self) -> bool:
        """Whether provider supports real-time search."""
        pass
    
    @property
    def is_available(self) -> bool:
        """Check if provider is available for queries."""
        if not self.config.enabled:
            return False
        if self._circuit_open:
            return False
        if self._health.status == ProviderStatus.DOWN:
            return False
        return True
    
    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
        include_realtime: bool = False
    ) -> List[SearchResult]:
        """
        Execute search query.
        
        Args:
            query: Search query string
            num_results: Maximum number of results to return
            include_realtime: Include real-time sources if supported
            
        Returns:
            List of SearchResult objects
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> ProviderStatus:
        """
        Check provider health status.
        
        Returns:
            Current provider status
        """
        pass
    
    def record_success(self, latency_ms: float):
        """Record successful request."""
        self._health.last_success = datetime.now()
        self._health.consecutive_failures = 0
        self._health.total_requests += 1
        self._health.successful_requests += 1
        
        # Update average latency
        if self._health.avg_latency_ms == 0:
            self._health.avg_latency_ms = latency_ms
        else:
            self._health.avg_latency_ms = (
                0.9 * self._health.avg_latency_ms + 0.1 * latency_ms
            )
        
        # Reset circuit breaker
        self._circuit_open = False
        
        # Update status
        if self._health.status == ProviderStatus.DOWN:
            self._health.status = ProviderStatus.HEALTHY
    
    def record_failure(self, error: Optional[Exception] = None):
        """Record failed request."""
        self._health.last_failure = datetime.now()
        self._health.consecutive_failures += 1
        self._health.total_requests += 1
        
        # Update status based on failures
        if self._health.consecutive_failures >= 5:
            self._health.status = ProviderStatus.DOWN
            self._circuit_open = True
        elif self._health.consecutive_failures >= 2:
            self._health.status = ProviderStatus.DEGRADED
        
        # Check for rate limiting
        if error and "rate limit" in str(error).lower():
            self._health.status = ProviderStatus.RATE_LIMITED
    
    def get_health(self) -> ProviderHealth:
        """Get current health status."""
        return self._health
    
    def reset_circuit(self):
        """Reset circuit breaker (manual recovery)."""
        self._circuit_open = False
        self._health.consecutive_failures = 0
        self._health.status = ProviderStatus.HEALTHY
