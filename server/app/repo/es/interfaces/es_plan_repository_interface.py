
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple

from ....model.mongo.plan import Plan

class ESPlanRepositoryInterface(ABC):
    """
    Abstract interface for Elasticsearch plan search and indexing.
    
    Implementations:
    - ESPlanRepository - Production Elasticsearch implementation
    - MockESPlanRepository - For unit testing
    - NullESPlanRepository - No-op for graceful degradation
    """
    
    # =========================================================================
    # INDEX MANAGEMENT
    # =========================================================================
    
    @abstractmethod
    def create_index(self, delete_if_exists: bool = False) -> bool:
        """Create the plan index with proper mapping."""
        pass
    
    @abstractmethod
    def delete_index(self) -> bool:
        """Delete the plan index."""
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
    def index_plan(self, plan: Plan) -> bool:
        """Index a single Plan model instance."""
        pass
    
    @abstractmethod
    def index_plans_bulk(self, plans: List[Plan]) -> bool:
        """Index multiple Plan model instances in bulk."""
        pass
    
    # =========================================================================
    # SEARCHING
    # =========================================================================
    
    @abstractmethod
    def search_plans(self, query: str, limit: int = 10, offset: int = 0) -> Tuple[List[Plan], int]:
        """Search for plans matching the query string."""
        pass