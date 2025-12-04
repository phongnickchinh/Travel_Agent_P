"""
Base Provider Interface for external POI data sources
All provider implementations must inherit from this abstract class
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseProvider(ABC):
    """
    Abstract base class for POI data providers (Google Places, TripAdvisor, etc.)
    """
    
    @abstractmethod
    def search(self, query: str, location: Dict[str, float], **kwargs) -> List[Dict]:
        """
        Search for places based on text query and location
        
        Args:
            query: Search query string (e.g., "restaurants", "hotels")
            location: Dict with 'latitude' and 'longitude' keys
            **kwargs: Additional search parameters:
                - radius: Search radius in meters (default: 5000)
                - max_results: Maximum number of results (default: 20)
                - types: List of place types to filter
                - min_rating: Minimum rating (0-5)
                - price_level: Price level filter
                - open_now: Only return currently open places
                
        Returns:
            List of place dictionaries with standardized schema
            
        Example:
            >>> provider.search(
            ...     "restaurants",
            ...     {"latitude": 16.0544, "longitude": 108.2428},
            ...     radius=2000,
            ...     min_rating=4.0
            ... )
        """
        pass
    
    @abstractmethod
    def get_details(self, place_id: str) -> Dict:
        """
        Get detailed information about a specific place
        
        Args:
            place_id: Provider-specific place identifier
            
        Returns:
            Detailed place information dictionary
            
        Example:
            >>> provider.get_details("ChIJv3H_AT8ZQjERWohner53iwk")
        """
        pass
    
    @abstractmethod
    def get_photos(self, photo_reference: str, max_width: int = 400, max_height: int = 400) -> str:
        """
        Get photo URL from photo reference
        
        Args:
            photo_reference: Provider-specific photo reference/name
            max_width: Maximum width in pixels
            max_height: Maximum height in pixels
            
        Returns:
            Photo URL string
            
        Example:
            >>> provider.get_photos("places/.../photos/...", max_width=800)
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this provider
        
        Returns:
            Provider name (e.g., "google_places", "tripadvisor")
        """
        pass
    
    def transform_to_poi(self, raw_data: Dict) -> Dict:
        """
        Transform provider-specific data to standardized POI schema
        
        This is a template method that can be overridden by subclasses
        Default implementation returns raw data as-is
        
        Args:
            raw_data: Raw data from provider API
            
        Returns:
            Standardized POI dictionary matching app/model/poi.py schema
        """
        return raw_data
