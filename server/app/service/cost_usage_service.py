"""
Cost Usage Service
==================

Business logic for cost usage tracking and analytics.

Author: Travel Agent P Team
Date: October 27, 2025
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..repo.postgre.interfaces.cost_usage_interface import CostUsageInterface

logger = logging.getLogger(__name__)


class CostUsageService:
    """
    Service layer for cost usage operations.
    
    Handles business logic for cost tracking and analytics.
    """
    
    def __init__(self, cost_usage_repo: CostUsageInterface):
        """
        Initialize service with repository.
        
        Args:
            cost_usage_repo: Cost usage repository instance
        """
        self.cost_usage_repo = cost_usage_repo
    
    def track_api_call(
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
        metadata: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track an API call cost.
        
        Returns:
            Dict representation of created cost record
        """
        try:
            cost_record = self.cost_usage_repo.create(
                provider=provider,
                service=service,
                endpoint=endpoint,
                method=method,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                status_code=status_code,
                success=success,
                user_id=user_id,
                plan_id=plan_id,
                request_id=request_id,
                extra_metadata=metadata,
                error_message=error_message,
                commit=True
            )
            
            return cost_record.to_display_dict()
        
        except Exception as e:
            logger.error(f"Failed to track API call: {e}")
            raise
    
    def get_plan_cost_summary(self, plan_id: str) -> Dict[str, Any]:
        """
        Get cost summary for a plan.
        
        Returns:
            Dict with total cost, request count, and provider breakdown
        """
        try:
            records = self.cost_usage_repo.get_by_plan_id(plan_id)
            
            if not records:
                return {
                    'plan_id': plan_id,
                    'total_cost': 0.0,
                    'total_requests': 0,
                    'providers': {}
                }
            
            # Calculate totals
            total_cost = sum(float(r.cost_usd) for r in records)
            total_requests = len(records)
            
            # Group by provider
            providers = {}
            for record in records:
                provider = record.provider
                if provider not in providers:
                    providers[provider] = {
                        'cost': 0.0,
                        'requests': 0,
                        'avg_latency_ms': 0
                    }
                
                providers[provider]['cost'] += float(record.cost_usd)
                providers[provider]['requests'] += 1
                
                if record.latency_ms:
                    # Calculate running average
                    prev_avg = providers[provider]['avg_latency_ms']
                    n = providers[provider]['requests']
                    providers[provider]['avg_latency_ms'] = (
                        (prev_avg * (n - 1) + record.latency_ms) / n
                    )
            
            return {
                'plan_id': plan_id,
                'total_cost': total_cost,
                'total_requests': total_requests,
                'providers': providers
            }
        
        except Exception as e:
            logger.error(f"Failed to get plan cost summary: {e}")
            raise
    
    def get_user_cost_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get cost summary for a user over last N days.
        
        Returns:
            Dict with total cost, request count, and daily breakdown
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get total cost
            total_cost = self.cost_usage_repo.get_total_cost(
                start_date=start_date,
                end_date=end_date,
                user_id=user_id
            )
            
            # Get daily breakdown
            records = self.cost_usage_repo.get_by_user_id(
                user_id=user_id,
                limit=1000
            )
            
            # Filter by date range
            filtered_records = [
                r for r in records
                if start_date <= r.created_at <= end_date
            ]
            
            return {
                'user_id': user_id,
                'period_days': days,
                'total_cost': total_cost,
                'total_requests': len(filtered_records),
                'avg_cost_per_request': total_cost / len(filtered_records) if filtered_records else 0
            }
        
        except Exception as e:
            logger.error(f"Failed to get user cost summary: {e}")
            raise
    
    def get_daily_cost_report(
        self,
        days: int = 7,
        provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily cost report for last N days.
        
        Returns:
            List of daily cost breakdowns
        """
        try:
            return self.cost_usage_repo.get_daily_cost(
                days=days,
                provider=provider
            )
        except Exception as e:
            logger.error(f"Failed to get daily cost report: {e}")
            raise
    
    def get_provider_comparison(
        self,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Compare costs across providers.
        
        Returns:
            List of provider stats sorted by cost
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            return self.cost_usage_repo.get_cost_by_provider(
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            logger.error(f"Failed to get provider comparison: {e}")
            raise
    
    def get_provider_health(self, provider: str, days: int = 1) -> Dict[str, Any]:
        """
        Get health metrics for a provider.
        
        Returns:
            Dict with success rate, latency stats, etc.
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            stats = self.cost_usage_repo.get_performance_stats(
                provider=provider,
                start_date=start_date,
                end_date=end_date
            )
            
            # Add health status
            success_rate = stats.get('success_rate', 0)
            avg_latency = stats.get('latency', {}).get('avg_ms')
            
            if success_rate >= 99:
                health_status = 'healthy'
            elif success_rate >= 95:
                health_status = 'degraded'
            else:
                health_status = 'unhealthy'
            
            stats['health_status'] = health_status
            stats['period_days'] = days
            
            return stats
        
        except Exception as e:
            logger.error(f"Failed to get provider health: {e}")
            raise
    
    def cleanup_old_records(self, days: int = 90) -> int:
        """
        Clean up old cost records.
        
        Returns:
            Number of records deleted
        """
        try:
            deleted_count = self.cost_usage_repo.delete_old_records(days=days)
            logger.info(f"Cleaned up {deleted_count} old cost records")
            return deleted_count
        
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
            raise
