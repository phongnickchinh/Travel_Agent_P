"""
Place Detail Repository Interface - MongoDB Data Access Layer
===============================================================

Purpose:
- Define abstract interface for PlaceDetail repository operations
- Enable dependency injection and unit testing
- Ensure consistent API across implementations

Author: Travel Agent P Team
Date: December 24, 2025
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class PlaceDetailRepositoryInterface(ABC):
    """
    Abstract interface for Place Detail data access.
    
    Implementations:
    - PlaceDetailRepository (MongoDB) - Production implementation
    - MockPlaceDetailRepository - For unit testing
    
    Features:
    - Get place detail by place_id
    - Upsert place details
    - Bulk operations
    - Access count tracking
    """
    
    @abstractmethod
    def get_by_place_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get place detail by place_id.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            PlaceDetail dict or None if not found
            
        Example:
            detail = repo.get_by_place_id("ChIJN1t_tDeuEmsRUsoyG83frY4")
            if detail:
                print(f"Found: {detail['name']}")
        """
        pass
    
    @abstractmethod
    def upsert(self, place_detail) -> bool:
        """
        Create or update place detail.
        
        Args:
            place_detail: PlaceDetail model instance
            
        Returns:
            True if successful, False otherwise
            
        Example:
            from app.model.mongo.place_detail import PlaceDetail
            
            detail = PlaceDetail(place_id="ChIJ...", name="Da Nang", ...)
            success = repo.upsert(detail)
        """
        pass
    
    @abstractmethod
    def upsert_from_dict(self, data: Dict[str, Any]) -> bool:
        """
        Create or update place detail from dict.
        
        Args:
            data: PlaceDetail data as dict (from Google API or other source)
            
        Returns:
            True if successful, False otherwise
            
        Example:
            google_data = {
                "place_id": "ChIJ...",
                "name": "Da Nang",
                "geometry": {"location": {"lat": 16.0544, "lng": 108.2428}},
                ...
            }
            success = repo.upsert_from_dict(google_data)
        """
        pass
    
    @abstractmethod
    def delete(self, place_id: str) -> bool:
        """
        Delete place detail by place_id.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            True if deleted, False if not found or error
            
        Example:
            success = repo.delete("ChIJN1t_tDeuEmsRUsoyG83frY4")
        """
        pass
    
    @abstractmethod
    def get_popular(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get most popular place details (by access count).
        
        Args:
            limit: Maximum results to return
            
        Returns:
            List of PlaceDetail dicts sorted by access_count descending
            
        Example:
            popular = repo.get_popular(limit=10)
            for place in popular:
                print(f"{place['name']}: {place['access_count']} accesses")
        """
        pass
    
    @abstractmethod
    def find_by_type(self, place_type: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Find place details by type.
        
        Args:
            place_type: Place type (e.g., 'locality', 'country', 'administrative_area')
            limit: Maximum results to return
            
        Returns:
            List of PlaceDetail dicts matching the type
            
        Example:
            cities = repo.find_by_type('locality', limit=50)
        """
        pass
    
    @abstractmethod
    def bulk_upsert(self, place_details: List) -> Dict[str, int]:
        """
        Bulk upsert place details.
        
        Args:
            place_details: List of PlaceDetail model instances
            
        Returns:
            Dict with counts: {'inserted': int, 'updated': int, 'failed': int}
            
        Example:
            details = [detail1, detail2, detail3]
            result = repo.bulk_upsert(details)
            print(f"Inserted: {result['inserted']}, Updated: {result['updated']}")
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Count total place details in collection.
        
        Returns:
            Total document count
            
        Example:
            total = repo.count()
            print(f"Total place details: {total}")
        """
        pass
