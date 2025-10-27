"""
Cost Usage Repository Interface
================================

Abstract interface for cost_usage data access.
Defines contract for repository implementations.

Author: Travel Agent P Team
Date: October 27, 2025
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from ....model.cost_usage import CostUsage as CostUsageModel


class CostUsageInterface(ABC):
    """Abstract interface for Cost Usage repository operations."""
    
    def __init__(self):
        pass
    
    # --- CREATE OPERATIONS ---
    
    @abstractmethod
    def create(
        self,
        provider: str,
        service: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost_usd: float = 0.0,
        latency_ms: Optional[int] = None,
        status_code: Optional[int] = None,
        success: bool = True,
        user_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        request_id: Optional[str] = None,
        extra_metadata: Optional[Dict] = None,
        error_message: Optional[str] = None,
        commit: bool = True
    ) -> CostUsageModel:
        """
        Create a new cost usage record.
        
        Args:
            provider: Provider name (google_places, openai, etc.)
            service: Service/API name
            endpoint: API endpoint
            method: HTTP method
            tokens_input: Input tokens
            tokens_output: Output tokens
            cost_usd: Cost in USD
            latency_ms: Response latency
            status_code: HTTP status code
            success: Whether request succeeded
            user_id: User ID (UUID string)
            plan_id: Plan ID
            request_id: Request ID for tracing
            metadata: Additional metadata
            error_message: Error message if failed
            commit: If True, commit to DB immediately
            
        Returns:
            Created CostUsageModel instance
        """
        pass
    
    # --- READ OPERATIONS ---
    
    @abstractmethod
    def get_by_id(self, cost_id: str) -> Optional[CostUsageModel]:
        """Get cost record by ID."""
        pass
    
    @abstractmethod
    def get_by_provider(
        self,
        provider: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[CostUsageModel]:
        """Get cost records by provider with pagination."""
        pass
    
    @abstractmethod
    def get_by_plan_id(self, plan_id: str) -> List[CostUsageModel]:
        """Get all cost records for a plan."""
        pass
    
    @abstractmethod
    def get_by_user_id(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[CostUsageModel]:
        """Get cost records by user with pagination."""
        pass
    
    @abstractmethod
    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        provider: Optional[str] = None
    ) -> List[CostUsageModel]:
        """Get cost records within date range, optionally filtered by provider."""
        pass
    
    # --- ANALYTICS OPERATIONS ---
    
    @abstractmethod
    def get_total_cost(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        provider: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> float:
        """
        Get total cost with optional filters.
        
        Returns:
            Total cost in USD
        """
        pass
    
    @abstractmethod
    def get_daily_cost(
        self,
        days: int = 7,
        provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily cost breakdown for last N days.
        
        Returns:
            List of dicts with date, cost, and request count
        """
        pass
    
    @abstractmethod
    def get_cost_by_provider(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get cost breakdown by provider.
        
        Returns:
            List of dicts with provider stats
        """
        pass
    
    @abstractmethod
    def get_performance_stats(
        self,
        provider: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get performance statistics for a provider.
        
        Returns:
            Dict with performance metrics (latency, success rate, etc.)
        """
        pass
    
    # --- DELETE OPERATIONS ---
    
    @abstractmethod
    def delete_old_records(self, days: int = 90) -> int:
        """
        Delete cost records older than N days.
        
        Returns:
            Number of records deleted
        """
        pass
