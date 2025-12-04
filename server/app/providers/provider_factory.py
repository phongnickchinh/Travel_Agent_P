"""
Provider Factory
Creates and manages provider instances based on configuration
"""

import os
import logging
from typing import List, Optional

from .base_provider import BaseProvider
from .google_places_provider import GooglePlacesProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """
    Factory for creating POI data provider instances
    
    Manages which providers are enabled based on:
    - Environment variables (API keys)
    - Feature flags
    - Configuration settings
    
    Example:
        # Get all available providers
        providers = ProviderFactory.get_providers()
        
        # Get specific provider
        google = ProviderFactory.get_google_places_provider()
    """
    
    _google_places_instance: Optional[GooglePlacesProvider] = None
    
    @classmethod
    def get_google_places_provider(cls) -> Optional[GooglePlacesProvider]:
        """
        Get Google Places provider instance (singleton)
        
        Returns:
            GooglePlacesProvider instance or None if not configured
        """
        if cls._google_places_instance is None:
            api_key = os.getenv('GOOGLE_PLACES_API_KEY')
            
            if api_key:
                cls._google_places_instance = GooglePlacesProvider(api_key=api_key)
                logger.info("Google Places provider initialized")
            else:
                logger.warning("GOOGLE_PLACES_API_KEY not found - Google Places provider disabled")
        
        return cls._google_places_instance
    
    @classmethod
    def get_providers(cls) -> List[BaseProvider]:
        """
        Get all available and enabled providers
        
        Checks for:
        - API key presence
        - Feature flags
        - Configuration settings
        
        Returns:
            List of enabled provider instances
        """
        providers = []
        
        # Google Places (required, always try to enable)
        google_places = cls.get_google_places_provider()
        if google_places:
            providers.append(google_places)
        
        # TripAdvisor (Week 5, feature flag controlled)
        if os.getenv('FEATURE_TRIPADVISOR_ENABLED', 'false').lower() == 'true':
            tripadvisor_key = os.getenv('TRIPADVISOR_API_KEY')
            if tripadvisor_key:
                # from .tripadvisor_provider import TripAdvisorProvider
                # providers.append(TripAdvisorProvider(api_key=tripadvisor_key))
                logger.info("TripAdvisor provider would be enabled (not implemented yet)")
        
        # Log active providers
        provider_names = [p.get_provider_name() for p in providers]
        logger.info(f"Active POI providers: {provider_names}")
        
        if not providers:
            logger.error("No POI providers available! Check API key configuration.")
        
        return providers
    
    @classmethod
    def get_provider_by_name(cls, name: str) -> Optional[BaseProvider]:
        """
        Get specific provider by name
        
        Args:
            name: Provider name ('google_places', 'tripadvisor', etc.)
            
        Returns:
            Provider instance or None if not found
        """
        providers = cls.get_providers()
        
        for provider in providers:
            if provider.get_provider_name() == name:
                return provider
        
        logger.warning(f"Provider '{name}' not found or not enabled")
        return None
    
    @classmethod
    def reset(cls):
        """
        Reset all cached provider instances
        Useful for testing or configuration changes
        """
        cls._google_places_instance = None
        logger.info("Provider factory reset")
