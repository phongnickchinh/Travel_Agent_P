"""
Elasticsearch Autocomplete Repository Interface
================================================

Purpose:
- Define abstract interface for ES autocomplete operations
- Enable dependency injection and unit testing
- Support graceful degradation when ES unavailable

Author: Travel Agent P Team
Date: December 22, 2025
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple

from ....model.mongo.autocomplete_cache import AutocompleteItem, CacheStatus


class ESAutocompleteRepositoryInterface(ABC):
    """
    Abstract interface for Elasticsearch autocomplete search and indexing.
    
    Implementations:
    - ESAutocompleteRepository - Production Elasticsearch implementation
    - MockESAutocompleteRepository - For unit testing
    - NullESAutocompleteRepository - No-op for graceful degradation
    """
    
    # =========================================================================
    # INDEX MANAGEMENT
    # =========================================================================
    
    @abstractmethod
    def create_index(self, delete_if_exists: bool = False) -> bool:
        """Create the autocomplete index with proper mapping."""
        pass
    
    @abstractmethod
    def delete_index(self) -> bool:
        """Delete the autocomplete index."""
        pass
    
    @abstractmethod
    def index_exists(self) -> bool:
        """Check if index exists."""
        pass
    
    @abstractmethod
    def ensure_index(self) -> bool:
        """Ensure index exists, create if not."""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Count total documents in index."""
        pass
    
    # =========================================================================
    # INDEXING
    # =========================================================================
    
    @abstractmethod
    def index_item(self, item: Dict[str, Any]) -> bool:
        """Index a single autocomplete item."""
        pass
    
    @abstractmethod
    def index_from_model(self, item: AutocompleteItem) -> bool:
        """Index an AutocompleteItem model instance."""
        pass
    
    @abstractmethod
    def bulk_index(self, items: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Bulk index multiple autocomplete items."""
        pass
    
    # =========================================================================
    # SEARCH
    # =========================================================================
    
    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 10,
        types: Optional[List[str]] = None,
        location: Optional[Dict[str, float]] = None,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Autocomplete search with edge n-gram matching."""
        pass
    
    @abstractmethod
    def get_by_place_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get autocomplete item by place_id."""
        pass
    
    @abstractmethod
    def exists(self, place_id: str) -> bool:
        """Check if item exists in index."""
        pass
    
    # =========================================================================
    # UPDATES
    # =========================================================================
    
    @abstractmethod
    def update_status(self, place_id: str, status: CacheStatus) -> bool:
        """Update item status (pending -> cached)."""
        pass
    
    @abstractmethod
    def increment_click(self, place_id: str) -> bool:
        """Increment click_count for popularity tracking."""
        pass
    
    @abstractmethod
    def update_location(self, place_id: str, lat: float, lng: float) -> bool:
        """Update item location (after resolving Place Details)."""
        pass
    
    # =========================================================================
    # DELETE
    # =========================================================================
    
    @abstractmethod
    def delete_by_place_id(self, place_id: str) -> bool:
        """Delete item by place_id."""
        pass
    
    @abstractmethod
    def delete_stale_items(self, days: int = 90) -> int:
        """Delete items not clicked in X days."""
        pass
