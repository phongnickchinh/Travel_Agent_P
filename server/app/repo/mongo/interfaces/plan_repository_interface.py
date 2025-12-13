"""
Plan Repository Interface - MongoDB Data Access Layer
======================================================

Purpose:
- Define abstract interface for Plan repository operations
- Enable dependency injection and unit testing
- Ensure consistent API across implementations

Author: Travel Agent P Team
Date: Week 4 - HuggingFace + LangChain Integration
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from ....model.mongo.plan import PlanStatusEnum


class PlanRepositoryInterface(ABC):
    """
    Abstract interface for Plan (Travel Itinerary) data access.
    
    Implementations:
    - PlanRepository (MongoDB) - Production implementation
    - MockPlanRepository - For unit testing
    
    Features:
    - CRUD operations
    - Status lifecycle management
    - User-based queries with pagination
    - Itinerary update after LLM generation
    """
    
    @abstractmethod
    def create(self, plan) -> Dict[str, Any]:
        """
        Create new plan with auto-generated plan_id.
        
        Args:
            plan: Plan model instance
            
        Returns:
            Created plan document
        """
        pass
    
    @abstractmethod
    def get_by_id(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get plan by plan_id.
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            Plan document if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        status: Optional[PlanStatusEnum] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user's plans with pagination.
        
        Args:
            user_id: User identifier
            skip: Offset for pagination
            limit: Max results per page
            status: Filter by status (optional)
            
        Returns:
            List of plan documents (newest first)
        """
        pass
    
    @abstractmethod
    def update_status(
        self,
        plan_id: str,
        status: PlanStatusEnum,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update plan status (e.g., PENDING → PROCESSING).
        
        Args:
            plan_id: Plan identifier
            status: New status
            error_message: Error details (if FAILED)
            
        Returns:
            True if updated successfully
        """
        pass
    
    @abstractmethod
    def update_itinerary(
        self,
        plan_id: str,
        itinerary: List[Dict[str, Any]],
        llm_model: str,
        llm_response_raw: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update plan with generated itinerary (after LLM completes).
        
        Args:
            plan_id: Plan identifier
            itinerary: List of DayPlan dicts
            llm_model: HuggingFace model name
            llm_response_raw: Raw LLM output
            metadata: Cost, tokens, etc.
            
        Returns:
            True if updated successfully
        """
        pass
    
    @abstractmethod
    def delete(self, plan_id: str) -> bool:
        """
        Delete plan by plan_id.
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            True if deleted successfully
        """
        pass
    
    @abstractmethod
    def count_by_user(self, user_id: str, status: Optional[PlanStatusEnum] = None) -> int:
        """
        Count user's plans.
        
        Args:
            user_id: User identifier
            status: Filter by status (optional)
            
        Returns:
            Total plan count
        """
        pass

