"""
Provider abstraction layer for Open Dsearch.

Defines the interface that all search providers must implement,
along with common data structures and a provider registry.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable, AsyncIterator
from pathlib import Path
import json


class ProviderStatus(Enum):
    """Health status of a search provider."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


class ProviderCapability(Enum):
    """Capabilities that a provider may support."""
    WEB_SEARCH = auto()
    REALTIME_SEARCH = auto()
    CITATIONS = auto()
    SYNTHESIS = auto()
    MULTIMODAL = auto()
    CODE_SEARCH = auto()


@dataclass
class ProviderCapabilities:
    """Capabilities supported by a provider."""
    web_search: bool = True
    realtime_search: bool = False
    citations: bool = False
    synthesis: bool = False
    multimodal: bool = False
    code_search: bool = False
    max_results_per_query: int = 10
    supported_languages: List[str] = field(default_factory=lambda: ["en"])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert capabilities to dictionary."""
        return {
            "web_search": self.web_search,
            "realtime_search": self.realtime_search,
            "citations": self.citations,
            "synthesis": self.synthesis,
            "multimodal": self.multimodal,
            "code_search": self.code_search,
            "max_results_per_query": self.max_results_per_query,
            "supported_languages": self.supported_languages,
        }


@dataclass
class SearchResult:
    """
    Standardized search result across all providers.
    
    Attributes:
        title: Result title
        url: Source URL
        snippet: Text snippet/summary
        source: Provider name that returned this result
        score: Relevance score (0.0 - 1.0)
        metadata: Provider-specific metadata
        fetched_content: Full fetched content (if requested)
        timestamp: When the result was retrieved
    """
    title: str
    url: str
    snippet: str
    source: str = "unknown"
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    fetched_content: Optional[str] = None
    timestamp: Optional[datetime] = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "score": self.score,
            "metadata": self.metadata,
            "fetched_content": self.fetched_content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        """Create result from dictionary."""
        timestamp = None
        if data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            title=data["title"],
            url=data["url"],
            snippet=data["snippet"],
            source=data.get("source", "unknown"),
            score=data.get("score", 0.0),
            metadata=data.get("metadata", {}),
            fetched_content=data.get("fetched_content"),
            timestamp=timestamp,
        )


@dataclass
class ProviderConfig:
    """
    Configuration for a search provider.
    
    Attributes:
        api_key: API key for the provider
        timeout_seconds: Request timeout in seconds
        max_retries: Maximum number of retries on failure
        rate_limit_per_minute: Rate limit (requests per minute)
        enabled: Whether this provider is enabled
        priority: Provider priority (lower = higher priority)
        extra: Provider-specific configuration
    """
    api_key: str
    timeout_seconds: float = 30.0
    max_retries: int = 3
    rate_limit_per_minute: int = 60
    enabled: bool = True
    priority: int = 1
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (excludes sensitive data)."""
        return {
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "enabled": self.enabled,
            "priority": self.priority,
            "extra": self.extra,
        }


@dataclass
class ProviderHealth:
    """Health information for a provider."""
    status: ProviderStatus = ProviderStatus.UNKNOWN
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    average_latency_ms: float = 0.0
    success_rate_24h: float = 1.0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health to dictionary."""
        return {
            "status": self.status.value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "consecutive_failures": self.consecutive_failures,
            "average_latency_ms": self.average_latency_ms,
            "success_rate_24h": self.success_rate_24h,
            "error_message": self.error_message,
        }


class SearchProvider(ABC):
    """
    Abstract base class for all search providers.
    
    All search providers must implement this interface to be
    compatible with the Open Dsearch orchestration system.
    """
    
    def __init__(self, config: ProviderConfig):
        """Initialize provider with configuration."""
        self.config = config
        self._health = ProviderHealth()
        self._capabilities: Optional[ProviderCapabilities] = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass
    
    @property
    def health(self) -> ProviderHealth:
        """Return current health status."""
        return self._health
    
    @property
    def capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities."""
        if self._capabilities is None:
            self._capabilities = self._get_capabilities()
        return self._capabilities
    
    @abstractmethod
    def _get_capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities. Override in subclass."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
        include_realtime: bool = False,
        **kwargs
    ) -> List[SearchResult]:
        """
        Execute search query.
        
        Args:
            query: Search query string
            num_results: Number of results to return
            include_realtime: Include real-time sources if supported
            **kwargs: Provider-specific options
            
        Returns:
            List of search results
            
        Raises:
            ProviderError: If search fails
            RateLimitError: If rate limited
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> ProviderStatus:
        """
        Check provider health.
        
        Returns:
            Current health status
        """
        pass


class ProviderRegistry:
    """
    Registry for managing search providers.
    
    Provides a central location to register and retrieve
    provider implementations.
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._providers: Dict[str, type] = {}
        self._instances: Dict[str, SearchProvider] = {}
    
    def register(self, name: str, provider_class: type) -> None:
        """
        Register a provider class.
        
        Args:
            name: Provider identifier
            provider_class: Class implementing SearchProvider
            
        Raises:
            ValueError: If provider is not a SearchProvider subclass
        """
        if not issubclass(provider_class, SearchProvider):
            raise ValueError(
                f"Provider {name} must inherit from SearchProvider"
            )
        self._providers[name] = provider_class
    
    def unregister(self, name: str) -> None:
        """Remove a provider from registry."""
        self._providers.pop(name, None)
        self._instances.pop(name, None)
    
    def create(
        self,
        name: str,
        config: ProviderConfig
    ) -> SearchProvider:
        """
        Create a provider instance.
        
        Args:
            name: Provider identifier
            config: Provider configuration
            
        Returns:
            Provider instance
            
        Raises:
            KeyError: If provider not registered
        """
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' not registered")
        
        provider = self._providers[name](config)
        self._instances[name] = provider
        return provider
    
    def get(self, name: str) -> Optional[SearchProvider]:
        """Get existing provider instance."""
        return self._instances.get(name)
    
    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        return list(self._providers.keys())
    
    def get_enabled_providers(self) -> List[SearchProvider]:
        """Get all enabled provider instances."""
        return [
            p for p in self._instances.values()
            if p.config.enabled
        ]
    
    def health_check_all(self) -> Dict[str, ProviderStatus]:
        """Check health of all providers."""
        return {
            name: provider.health.status
            for name, provider in self._instances.items()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Export registry state as dictionary."""
        return {
            "registered": list(self._providers.keys()),
            "instances": {
                name: {
                    "health": provider.health.to_dict(),
                    "capabilities": provider.capabilities.to_dict(),
                    "config": provider.config.to_dict(),
                }
                for name, provider in self._instances.items()
            },
        }


# Global registry instance
_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    """Get or create global provider registry."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


def reset_registry() -> None:
    """Reset global registry (useful for testing)."""
    global _registry
    _registry = None