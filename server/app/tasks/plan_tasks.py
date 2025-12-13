"""
Celery Tasks - Async Plan Generation
=====================================

Purpose:
- Background task for LLM-based itinerary generation
- Asynchronous plan processing
- Error handling and status updates

Author: Travel Agent P Team
Date: Week 4 - HuggingFace + LangChain Integration
"""

import logging

logger = logging.getLogger(__name__)


def get_celery_app():
    """Lazy import celery to avoid circular imports."""
    from app import celery
    return celery


def get_planner_service():
    """Create PlannerService instance with proper DI."""
    from app.repo.mongo.plan_repository import PlanRepository
    from app.repo.postgre.implementations.cost_usage_repository import CostUsageRepository
    from app.service.planner_service import PlannerService
    from app.service.cost_usage_service import CostUsageService
    
    plan_repo = PlanRepository()
    cost_usage_repo = CostUsageRepository()
    cost_usage_service = CostUsageService(cost_usage_repo)
    
    return PlannerService(plan_repo, cost_usage_service)


# Get celery instance
celery = get_celery_app()


@celery.task(name='app.tasks.plan_tasks.generate_plan_task', bind=True, max_retries=3)
def generate_plan_task(self, plan_id: str):
    """
    Celery task to generate travel itinerary using LangChain.
    
    Args:
        plan_id: Plan identifier
        
    Returns:
        Dict with result status
        
    Usage:
        # Trigger async
        generate_plan_task.delay("plan_abc123")
        
        # Trigger with countdown
        generate_plan_task.apply_async(args=["plan_abc123"], countdown=5)
    """
    try:
        logger.info(f"[CELERY] Starting plan generation for: {plan_id}")
        
        # Initialize service using helper function
        planner_service = get_planner_service()
        
        # Generate itinerary (synchronous within worker)
        success = planner_service.generate_itinerary(plan_id)
        
        if success:
            logger.info(f"[CELERY] Successfully generated plan: {plan_id}")
            return {
                "status": "success",
                "plan_id": plan_id,
                "message": "Itinerary generated successfully"
            }
        else:
            logger.error(f"[CELERY] Failed to generate plan: {plan_id}")
            return {
                "status": "failed",
                "plan_id": plan_id,
                "message": "LangChain generation failed"
            }
            
    except Exception as e:
        logger.error(f"[CELERY] Exception in plan generation for {plan_id}: {e}")
        
        # Retry with exponential backoff
        try:
            raise self.retry(exc=e, countdown=2 ** self.request.retries)
        except self.MaxRetriesExceededError:
            logger.error(f"[CELERY] Max retries exceeded for plan {plan_id}")
            
            # Mark plan as FAILED
            planner_service = get_planner_service()
            from app.model.mongo.plan import PlanStatusEnum
            planner_service.plan_repo.update_status(
                plan_id,
                PlanStatusEnum.FAILED,
                error_message=f"Celery task failed after {self.max_retries} retries: {str(e)}"
            )
            
            return {
                "status": "failed",
                "plan_id": plan_id,
                "message": f"Task failed after retries: {str(e)}"
            }


# Optional: Add periodic task to cleanup old FAILED plans
@celery.task(name='app.tasks.plan_tasks.cleanup_failed_plans')
def cleanup_failed_plans():
    """
    Periodic task to cleanup old FAILED plans (optional).
    
    Configure in Celery beat schedule:
    CELERYBEAT_SCHEDULE = {
        'cleanup-failed-plans': {
            'task': 'app.tasks.plan_tasks.cleanup_failed_plans',
            'schedule': crontab(hour=2, minute=0),  # Daily at 2am
        }
    }
    """
    from datetime import datetime, timedelta
    from app.repo.mongo.plan_repository import PlanRepository
    from app.model.mongo.plan import PlanStatusEnum
    
    logger.info("[CELERY] Running cleanup_failed_plans task")
    
    try:
        plan_repo = PlanRepository()
        
        # Delete FAILED plans older than 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        result = plan_repo.collection.delete_many({
            "status": PlanStatusEnum.FAILED.value,
            "updated_at": {"$lt": cutoff_date}
        })
        
        logger.info(f"[CELERY] Deleted {result.deleted_count} old FAILED plans")
        return {"deleted_count": result.deleted_count}
        
    except Exception as e:
        logger.error(f"[CELERY] Cleanup task failed: {e}")
        return {"error": str(e)}
