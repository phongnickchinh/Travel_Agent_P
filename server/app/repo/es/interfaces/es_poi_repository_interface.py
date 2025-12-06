"""
Elasticsearch POI Repository Interface
========================================

Purpose:
- Define abstract interface for Elasticsearch POI operations
- Enable dependency injection and unit testing
- Support graceful degradation when ES unavailable

Author: Travel Agent P Team
Date: November 27, 2025
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple


class ESPOIRepositoryInterface(ABC):
    """
    Abstract interface for Elasticsearch POI search and indexing.
    
    Implementations:
    - ESPOIRepository - Production Elasticsearch implementation
    - MockESPOIRepository - For unit testing
    - NullESPOIRepository - No-op for graceful degradation
    
    Features:
    - Index management
    - Bulk indexing
    - Autocomplete search
    - Geo-distance search
    - Full-text search with filters
    """
    
    @abstractmethod
    def create_index(self, delete_if_exists: bool = False) -> bool:
        """
        Create the POI index with proper mapping.
        
        Args:
            delete_if_exists: If True, delete existing index first
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_index(self) -> bool:
        """
        Delete the POI index.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def index_poi(self, poi_data: Dict, poi_id: Optional[str] = None) -> bool:
        """
        Index a single POI document.
        
        Args:
            poi_data: POI data dictionary
            poi_id: Optional document ID (uses poi_id from data if not provided)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def bulk_index(self, pois: List[Dict]) -> Tuple[int, int]:
        """
        Bulk index multiple POI documents.
        
        Args:
            pois: List of POI data dictionaries
            
        Returns:
            Tuple of (success_count, error_count)
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query: str,
        location: Optional[Dict[str, float]] = None,
        radius_km: Optional[float] = None,
        types: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        price_levels: Optional[List[str]] = None,
        sort_by: str = "relevance",
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search POIs with full-text, geo, and filter support.
        
        Args:
            query: Search query string
            location: {"latitude": float, "longitude": float}
            radius_km: Search radius in kilometers
            types: POI types filter
            min_rating: Minimum rating (0-5)
            price_levels: Price level filter
            sort_by: Sort order ("relevance", "distance", "rating", "popularity")
            limit: Max results
            offset: Pagination offset
            
        Returns:
            {
                "results": [POI dicts with _score and optional _distance_km],
                "total": int,
                "took_ms": int
            }
        """
        pass
    
    @abstractmethod
    def autocomplete(self, prefix: str, size: int = 10) -> List[str]:
        """
        Autocomplete search using edge n-gram.
        
        Args:
            prefix: Search prefix (min 2 chars)
            size: Max number of suggestions
            
        Returns:
            List of POI name suggestions
        """
        pass
    
    @abstractmethod
    def get_by_id(self, poi_id: str) -> Optional[Dict]:
        """
        Get POI by ID from Elasticsearch.
        
        Args:
            poi_id: POI identifier
            
        Returns:
            POI document if found, None otherwise
        """
        pass
    
    @abstractmethod
    def delete_poi(self, poi_id: str) -> bool:
        """
        Delete POI from Elasticsearch index.
        
        Args:
            poi_id: POI identifier
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if Elasticsearch connection is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
