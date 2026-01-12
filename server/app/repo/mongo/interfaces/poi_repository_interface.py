"""
POI Repository Interface - MongoDB Data Access Layer
======================================================

Purpose:
- Define abstract interface for POI repository operations
- Enable dependency injection and unit testing
- Ensure consistent API across implementations

Author: Travel Agent P Team
Date: November 27, 2025
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class POIRepositoryInterface(ABC):
    """
    Abstract interface for POI (Point of Interest) data access.
    
    Implementations:
    - POIRepository (MongoDB) - Production implementation
    - MockPOIRepository - For unit testing
    
    Features:
    - CRUD operations
    - Geo-spatial search
    - Text search
    - Deduplication
    - Write-through cache support
    """
    
    @abstractmethod
    def create(self, poi) -> Dict[str, Any]:
        """
        Create new POI with deduplication check.
        
        Args:
            poi: POI model instance
            
        Returns:
            Created POI document
            
        Raises:
            DuplicateKeyError: If dedupe_key already exists
            ValueError: If fuzzy duplicate found
        """
        pass
    
    @abstractmethod
    def get_by_id(self, poi_id: str) -> Optional[Dict[str, Any]]:
        """
        Get POI by ID.
        
        Args:
            poi_id: POI identifier
            
        Returns:
            POI document if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update(self, poi_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update POI by ID.
        
        Args:
            poi_id: POI identifier
            updates: Fields to update
            
        Returns:
            Updated POI document if found, None otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, poi_id: str) -> bool:
        """
        Delete POI by ID.
        
        Args:
            poi_id: POI identifier
            
        Returns:
            True if deleted, False otherwise
        """
        pass
    
    @abstractmethod
    def search(self, search_request) -> Dict[str, Any]:
        """
        Search POI with filters and pagination.
        
        Args:
            search_request: Search parameters (POISearchRequest)
            
        Returns:
            {
                "results": [POI documents],
                "total": total count,
                "page": current page,
                "limit": items per page,
                "total_pages": total pages
            }
        """
        pass
    
    @abstractmethod
    def get_by_category(self, category, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get POI by category.
        
        Args:
            category: Category to filter by
            limit: Max results
            
        Returns:
            List of POI documents
        """
        pass
    
    @abstractmethod
    def get_nearby(self, lat: float, lng: float, radius_km: float = 10, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get nearby POI within radius.
        
        Args:
            lat: Latitude
            lng: Longitude
            radius_km: Search radius in km
            limit: Max results
            
        Returns:
            List of POI documents with distance_km field
        """
        pass
    
    @abstractmethod
    def get_popular(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get popular POIs sorted by popularity score.
        
        Args:
            limit: Max results
            
        Returns:
            List of POI documents
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Count total POIs in collection.
        
        Returns:
            Total count
        """
        pass
    
    @abstractmethod
    def get_by_dedupe_key(self, dedupe_key: str) -> Optional[Dict[str, Any]]:
        """
        Get POI by deduplication key.
        
        Args:
            dedupe_key: Unique deduplication key
            
        Returns:
            POI document if found, None otherwise
        """
        pass
    
    # ========== Write-Through Cache Methods ==========
    
    @abstractmethod
    def upsert(self, poi) -> Dict[str, Any]:
        """
        Smart upsert with staleness check for write-through cache.
        
        Args:
            poi: POI model instance
            
        Returns:
            {
                **poi_dict,
                "_operation": "inserted" | "updated" | "skipped",
                "_reason": "new_poi" | "stale_data" | "fresh_data"
            }
        """
        pass
    
    @abstractmethod
    def bulk_upsert(self, pois: List) -> Dict[str, Any]:
        """
        Bulk upsert with smart staleness check.
        
        Args:
            pois: List of POI model instances
            
        Returns:
            {
                "total": int,
                "inserted": int,
                "updated": int,
                "skipped": int,
                "errors": int
            }
        """
        pass
    
    @abstractmethod
    def get_stale_pois(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get POIs that need to be refreshed.
        
        Args:
            limit: Max number of stale POIs to return
            
        Returns:
            List of stale POI documents
        """
        pass
    
    @abstractmethod
    def count_stale(self) -> int:
        """
        Count stale POIs that need refresh.
        
        Returns:
            Number of stale POIs
        """
        pass
