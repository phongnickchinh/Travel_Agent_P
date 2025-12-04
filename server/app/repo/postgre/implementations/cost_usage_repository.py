"""
Cost Usage Repository Implementation (PostgreSQL)
==================================================

Purpose:
- Data access layer for cost_usage table
- CRUD operations for cost tracking
- Analytics queries (daily cost, provider comparison, etc.)

Author: Travel Agent P Team  
Date: October 27, 2025
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import and_, func

from ..interfaces.cost_usage_interface import CostUsageInterface
from ....model.cost_usage import CostUsage as CostUsageModel
from .... import db

logger = logging.getLogger(__name__)


class CostUsageRepository(CostUsageInterface):
    """
    Repository for cost_usage data access.
    
    Features:
    - Create cost records with commit control
    - Query by provider, date range, user, plan
    - Aggregate costs (daily, weekly, monthly)
    - Performance analytics
    """
    
    def __init__(self):
        """Initialize repository."""
        pass
    
    # --- CREATE OPERATIONS ---
    
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
        
        Uses save() method from BaseModel with commit parameter.
        """
        try:
            cost_record = CostUsageModel(
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
                extra_metadata=extra_metadata,
                error_message=error_message
            )
            
            # Use save() from BaseModel with commit parameter
            cost_record.save(commit=commit)
            
            logger.info(
                f"[COST] Cost tracked: {provider}/{service} "
                f"${cost_usd:.6f} {latency_ms}ms"
            )
            
            return cost_record
        
        except Exception as e:
            logger.error(f"[COST] Failed to create cost record: {e}")
            raise
    
    # --- READ OPERATIONS ---
    
    def get_by_id(self, cost_id: str) -> Optional[CostUsageModel]:
        """Get cost record by ID."""
        return db.session.execute(
            db.select(CostUsageModel).where(
                and_(
                    CostUsageModel.id == cost_id,
                    CostUsageModel.is_deleted == False
                )
            )
        ).scalar_one_or_none()
    
    def get_by_provider(
        self,
        provider: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[CostUsageModel]:
        """
        Get cost records by provider with pagination.
        """
        return db.session.execute(
            db.select(CostUsageModel)
            .where(
                and_(
                    CostUsageModel.provider == provider,
                    CostUsageModel.is_deleted == False
                )
            )
            .order_by(CostUsageModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
    
    def get_by_plan_id(self, plan_id: str) -> List[CostUsageModel]:
        """Get all cost records for a plan."""
        return db.session.execute(
            db.select(CostUsageModel)
            .where(
                and_(
                    CostUsageModel.plan_id == plan_id,
                    CostUsageModel.is_deleted == False
                )
            )
            .order_by(CostUsageModel.created_at.asc())
        ).scalars().all()
    
    def get_by_user_id(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[CostUsageModel]:
        """Get cost records by user with pagination."""
        return db.session.execute(
            db.select(CostUsageModel)
            .where(
                and_(
                    CostUsageModel.user_id == user_id,
                    CostUsageModel.is_deleted == False
                )
            )
            .order_by(CostUsageModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
    
    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        provider: Optional[str] = None
    ) -> List[CostUsageModel]:
        """
        Get cost records within date range.
        """
        filters = [
            CostUsageModel.created_at >= start_date,
            CostUsageModel.created_at <= end_date,
            CostUsageModel.is_deleted == False
        ]
        
        if provider:
            filters.append(CostUsageModel.provider == provider)
        
        return db.session.execute(
            db.select(CostUsageModel)
            .where(and_(*filters))
            .order_by(CostUsageModel.created_at.asc())
        ).scalars().all()
    
    # --- ANALYTICS OPERATIONS ---
    
    def get_total_cost(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        provider: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> float:
        """
        Get total cost with optional filters.
        """
        filters = [CostUsageModel.is_deleted == False]
        
        if start_date:
            filters.append(CostUsageModel.created_at >= start_date)
        if end_date:
            filters.append(CostUsageModel.created_at <= end_date)
        if provider:
            filters.append(CostUsageModel.provider == provider)
        if user_id:
            filters.append(CostUsageModel.user_id == user_id)
        
        result = db.session.execute(
            db.select(func.sum(CostUsageModel.cost_usd))
            .where(and_(*filters))
        ).scalar()
        
        return float(result) if result else 0.0
    
    def get_daily_cost(
        self,
        days: int = 7,
        provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily cost breakdown for last N days.
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        filters = [
            CostUsageModel.created_at >= start_date,
            CostUsageModel.created_at <= end_date,
            CostUsageModel.is_deleted == False
        ]
        
        if provider:
            filters.append(CostUsageModel.provider == provider)
        
        results = db.session.execute(
            db.select(
                func.date(CostUsageModel.created_at).label('date'),
                func.sum(CostUsageModel.cost_usd).label('cost'),
                func.count(CostUsageModel.id).label('requests')
            )
            .where(and_(*filters))
            .group_by(func.date(CostUsageModel.created_at))
            .order_by(func.date(CostUsageModel.created_at).asc())
        ).all()
        
        return [
            {
                'date': str(row.date),
                'cost': float(row.cost),
                'requests': row.requests
            }
            for row in results
        ]
    
    def get_cost_by_provider(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get cost breakdown by provider.
        """
        filters = [CostUsageModel.is_deleted == False]
        
        if start_date:
            filters.append(CostUsageModel.created_at >= start_date)
        if end_date:
            filters.append(CostUsageModel.created_at <= end_date)
        
        results = db.session.execute(
            db.select(
                CostUsageModel.provider,
                func.sum(CostUsageModel.cost_usd).label('cost'),
                func.count(CostUsageModel.id).label('requests'),
                func.avg(CostUsageModel.latency_ms).label('avg_latency'),
                func.sum(CostUsageModel.tokens_total).label('total_tokens')
            )
            .where(and_(*filters))
            .group_by(CostUsageModel.provider)
            .order_by(func.sum(CostUsageModel.cost_usd).desc())
        ).all()
        
        return [
            {
                'provider': row.provider,
                'cost': float(row.cost),
                'requests': row.requests,
                'avg_latency_ms': float(row.avg_latency) if row.avg_latency else None,
                'total_tokens': row.total_tokens
            }
            for row in results
        ]
    
    def get_performance_stats(
        self,
        provider: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get performance statistics for a provider.
        """
        filters = [
            CostUsageModel.provider == provider,
            CostUsageModel.is_deleted == False
        ]
        
        if start_date:
            filters.append(CostUsageModel.created_at >= start_date)
        if end_date:
            filters.append(CostUsageModel.created_at <= end_date)
        
        # Total requests
        total_requests = db.session.execute(
            db.select(func.count(CostUsageModel.id))
            .where(and_(*filters))
        ).scalar()
        
        # Successful requests
        successful_requests = db.session.execute(
            db.select(func.count(CostUsageModel.id))
            .where(
                and_(
                    *filters,
                    CostUsageModel.success == True
                )
            )
        ).scalar()
        
        failed_requests = total_requests - successful_requests
        
        # Latency stats
        latency_filters = filters + [CostUsageModel.latency_ms.isnot(None)]
        
        latency = db.session.execute(
            db.select(
                func.avg(CostUsageModel.latency_ms).label('avg'),
                func.min(CostUsageModel.latency_ms).label('min'),
                func.max(CostUsageModel.latency_ms).label('max')
            )
            .where(and_(*latency_filters))
        ).first()
        
        return {
            'provider': provider,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            'latency': {
                'avg_ms': float(latency.avg) if latency.avg else None,
                'min_ms': latency.min,
                'max_ms': latency.max
            }
        }
    
    # --- DELETE OPERATIONS ---
    
    def delete_old_records(self, days: int = 90) -> int:
        """
        Delete cost records older than N days (soft delete).
        
        Uses soft_delete() from BaseModel.
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            old_records = db.session.execute(
                db.select(CostUsageModel)
                .where(
                    and_(
                        CostUsageModel.created_at < cutoff_date,
                        CostUsageModel.is_deleted == False
                    )
                )
            ).scalars().all()
            
            deleted_count = 0
            for record in old_records:
                record.soft_delete()
                deleted_count += 1
            
            logger.info(
                f"[COST] Soft deleted {deleted_count} old cost records "
                f"(older than {days} days)"
            )
            
            return deleted_count
        
        except Exception as e:
            logger.error(f"[COST] Failed to delete old records: {e}")
            raise
