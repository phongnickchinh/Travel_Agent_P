"""
Autocomplete Cache Repository Interface - MongoDB Data Access Layer
====================================================================

Purpose:
- Define abstract interface for autocomplete cache repository operations
- Enable dependency injection and unit testing
- Ensure consistent API across implementations

Author: Travel Agent P Team
Date: December 22, 2025
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class AutocompleteRepositoryInterface(ABC):
    """
    Abstract interface for Autocomplete Cache data access.
    
    Implementations:
    - AutocompleteRepository (MongoDB) - Production implementation
    - MockAutocompleteRepository - For unit testing
    
    Features:
    - CRUD operations for autocomplete cache
    - Text search fallback (when ES is down)
    - Click count management
    - Status update (pending → cached)
    """
    
    @abstractmethod
    def create(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new autocomplete cache item.
        
        Args:
            item: AutocompleteItem as dict
            
        Returns:
            Created document
            
        Raises:
            DuplicateKeyError: If place_id already exists
        """
        pass
    
    @abstractmethod
    def bulk_create(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Bulk create autocomplete cache items.
        
        Args:
            items: List of AutocompleteItem dicts
            
        Returns:
            {"inserted": count, "skipped": count}
        """
        pass
    
    @abstractmethod
    def upsert(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upsert (insert or update) autocomplete cache item.
        
        Args:
            item: AutocompleteItem as dict
            
        Returns:
            Upserted document
        """
        pass
    
    @abstractmethod
    def get_by_place_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get autocomplete item by place_id.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            Document if found, None otherwise
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 10,
        types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Text search for autocomplete (fallback when ES is down).
        
        Args:
            query: Search query
            limit: Maximum results
            types: Filter by place types
            
        Returns:
            List of matching documents
        """
        pass
    
    @abstractmethod
    def update_status(
        self,
        place_id: str,
        status: str,
        lat: Optional[float] = None,
        lng: Optional[float] = None
    ) -> bool:
        """
        Update status from pending to cached.
        
        Args:
            place_id: Google Place ID
            status: New status ("cached" or "pending")
            lat: Latitude (optional, set when resolving)
            lng: Longitude (optional, set when resolving)
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    def increment_click(self, place_id: str) -> bool:
        """
        Increment click_count for popularity tracking.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            True if updated, False if not found
        """
        pass
    
    @abstractmethod
    def delete_by_place_id(self, place_id: str) -> bool:
        """
        Delete autocomplete item by place_id.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    def count(self, status: Optional[str] = None) -> int:
        """
        Count documents in collection.
        
        Args:
            status: Optional filter by status
            
        Returns:
            Document count
        """
        pass
    
    @abstractmethod
    def get_popular(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get most popular autocomplete items by click_count.
        
        Args:
            limit: Maximum results
            
        Returns:
            List of popular items sorted by click_count desc
        """
        pass
    
    @abstractmethod
    def get_pending(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get pending items that need to be resolved.
        
        Args:
            limit: Maximum results
            
        Returns:
            List of pending items
        """
        pass
    
    @abstractmethod
    def delete_all(self) -> int:
        """
        Delete all documents (for testing/reset).
        
        Returns:
            Number of deleted documents
        """
        pass
