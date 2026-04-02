"""Provider registry and factory."""

from typing import Dict, List, Optional, Type

from .base import SearchProvider, ProviderConfig
from .gemini import GeminiProvider
from .minimax import MiniMaxProvider
from .kimi import KimiProvider


class ProviderRegistry:
    """Registry for search providers."""
    
    _providers: Dict[str, Type[SearchProvider]] = {
        "gemini": GeminiProvider,
        "minimax": MiniMaxProvider,
        "kimi": KimiProvider,
    }
    
    @classmethod
    def register(
        cls,
        name: str,
        provider_class: Type[SearchProvider]
    ) -> None:
        """
        Register a new provider.
        
        Args:
            name: Provider name
            provider_class: Provider class
        """
        cls._providers[name] = provider_class
    
    @classmethod
    def get_provider_class(cls, name: str) -> Optional[Type[SearchProvider]]:
        """
        Get provider class by name.
        
        Args:
            name: Provider name
            
        Returns:
            Provider class or None
        """
        return cls._providers.get(name)
    
    @classmethod
    def create_provider(
        cls,
        name: str,
        config: ProviderConfig
    ) -> Optional[SearchProvider]:
        """
        Create provider instance.
        
        Args:
            name: Provider name
            config: Provider configuration
            
        Returns:
            Provider instance or None
        """
        provider_class = cls.get_provider_class(name)
        if provider_class:
            return provider_class(config)
        return None
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """
        List all registered provider names.
        
        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
    
    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Unregister a provider.
        
        Args:
            name: Provider name
            
        Returns:
            True if removed, False if not found
        """
        if name in cls._providers:
            del cls._providers[name]
            return True
        return False
