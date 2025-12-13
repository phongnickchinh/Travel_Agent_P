"""
Planner Service - Travel Itinerary Business Logic
==================================================

Purpose:
- Orchestrate plan creation with LangChain
- Manage plan lifecycle (PENDING → PROCESSING → COMPLETED)
- Interface between controller and repository
- Handle errors and fallback logic
- Track API costs with real usage data

Author: Travel Agent P Team
Date: Week 4 - HuggingFace + LangChain Integration
"""

import logging
import time
from typing import List, Dict, Any, Optional

from ..model.mongo.plan import Plan, PlanStatusEnum, PlanCreateRequest, PlanUpdateRequest
from ..repo.mongo.plan_repository import PlanRepository
from .lc_chain import TravelPlannerChain
from .cost_usage_service import CostUsageService
from ..utils.sanitization import sanitize_user_input

logger = logging.getLogger(__name__)


class PlannerService:
    """
    Service layer for travel planning.
    
    Features:
    - Create plan (initialize with PENDING status)
    - Generate itinerary (LangChain orchestration)
    - Get user's plans
    - Update/regenerate plan
    - Delete plan
    
    Workflow:
    1. User requests plan → create() → status=PENDING
    2. Celery task → generate_itinerary() → LangChain → status=COMPLETED
    3. Error → status=FAILED
    """
    
    def __init__(
        self, 
        plan_repository: Optional[PlanRepository] = None,
        cost_usage_service: Optional[CostUsageService] = None
    ):
        """
        Initialize planner service.
        
        Args:
            plan_repository: Plan repository (auto-created if None)
            cost_usage_service: Cost tracking service (auto-created if None)
        """
        self.plan_repo = plan_repository or PlanRepository()
        self.cost_service = cost_usage_service or CostUsageService()
        logger.info("[INFO] PlannerService initialized")
    
    def create_plan(self, user_id: str, request: PlanCreateRequest) -> Dict[str, Any]:
        """
        Create new plan with PENDING status.
        
        Args:
            user_id: User identifier
            request: PlanCreateRequest payload
            
        Returns:
            Created plan dict
            
        Example:
            request = PlanCreateRequest(
                destination="Da Nang",
                num_days=3,
                preferences={"interests": ["beach", "culture"]}
            )
            plan = planner_service.create_plan("user123", request)
        """
        try:
            # Create Plan model
            plan = Plan(
                user_id=user_id,
                destination=request.destination,
                num_days=request.num_days,
                start_date=request.start_date,
                preferences=request.preferences,
                status=PlanStatusEnum.PENDING
            )
            
            # Save to MongoDB
            created_plan = self.plan_repo.create(plan)
            
            logger.info(
                f"[INFO] Created plan {created_plan['plan_id']} for user {user_id}: "
                f"{request.num_days} days in {request.destination}"
            )
            
            return created_plan
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to create plan: {e}")
            raise
    
    def generate_itinerary(self, plan_id: str) -> bool:
        """
        Generate itinerary using LangChain (synchronous).
        
        This method should be called by Celery worker (async).
        Tracks EXACT token usage and cost from API response.
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            True if generation succeeded
        """
        start_time = time.time()
        
        try:
            # Get plan
            plan = self.plan_repo.get_by_id(plan_id)
            if not plan:
                logger.error(f"[ERROR] Plan {plan_id} not found")
                return False
            
            user_id = plan.get('user_id')
            
            # Update status to PROCESSING
            self.plan_repo.update_status(plan_id, PlanStatusEnum.PROCESSING)
            logger.info(f"[INFO] Starting LangChain generation for plan {plan_id}")
            
            # Run LangChain
            chain = TravelPlannerChain()
            # Sanitize preferences before sending to LLM
            prefs = plan.get('preferences', {}) or {}
            sanitized_prefs = sanitize_user_input(prefs, ["interests", "budget", "pace", "dietary"]) if isinstance(prefs, dict) else {}

            result = chain.run({
                "destination": plan['destination'],
                "num_days": plan['num_days'],
                "start_date": plan.get('start_date'),
                "preferences": sanitized_prefs
            })
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            if result['success']:
                # Track EXACT cost from API response
                self._track_llm_usage(
                    result=result,
                    plan_id=plan_id,
                    user_id=user_id,
                    latency_ms=latency_ms,
                    success=True
                )
                
                # Update plan with itinerary
                self.plan_repo.update_itinerary(
                    plan_id=plan_id,
                    itinerary=result['itinerary'],
                    llm_model=result['model'],
                    llm_response_raw=result['llm_response_raw'],
                    metadata={
                        "generation_source": "langchain",
                        "chain_type": "lcel",
                        "provider": result.get('provider', 'unknown'),
                        "tokens_input": result.get('tokens_input', 0),
                        "tokens_output": result.get('tokens_output', 0),
                        "cost_usd": result.get('cost_usd', 0.0),
                        "latency_ms": latency_ms
                    }
                )
                logger.info(
                    f"[INFO] Successfully generated itinerary for plan {plan_id} | "
                    f"Provider: {result.get('provider')} | "
                    f"Tokens: {result.get('tokens_input', 0)}+{result.get('tokens_output', 0)} | "
                    f"Cost: ${result.get('cost_usd', 0):.6f}"
                )
                return True
            else:
                # Track failed attempt
                self._track_llm_usage(
                    result=result,
                    plan_id=plan_id,
                    user_id=user_id,
                    latency_ms=latency_ms,
                    success=False
                )
                
                # Mark as FAILED
                error_msg = result.get('error', 'LangChain execution failed')
                self.plan_repo.update_status(
                    plan_id,
                    PlanStatusEnum.FAILED,
                    error_message=error_msg
                )
                logger.error(f"[ERROR] LangChain failed for plan {plan_id}: {error_msg}")
                return False
                
        except Exception as e:
            # Mark as FAILED
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[ERROR] Itinerary generation failed for plan {plan_id}: {e}")
            self.plan_repo.update_status(
                plan_id,
                PlanStatusEnum.FAILED,
                error_message=str(e)
            )
            return False
    
    def _track_llm_usage(
        self,
        result: Dict[str, Any],
        plan_id: str,
        user_id: Optional[str],
        latency_ms: int,
        success: bool
    ) -> None:
        """
        Track LLM usage with EXACT data from API response.
        
        Args:
            result: Chain run result with usage stats
            plan_id: Plan ID
            user_id: User ID (optional)
            latency_ms: Request latency in milliseconds
            success: Whether the request was successful
        """
        try:
            provider = result.get('provider', 'unknown')
            model = result.get('model', 'unknown')
            tokens_input = result.get('tokens_input', 0)
            tokens_output = result.get('tokens_output', 0)
            cost_usd = result.get('cost_usd', 0.0)
            
            self.cost_service.track_api_call(
                provider=provider,
                api_name="llm_generate",
                endpoint=f"/chat/completions",
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                success=success,
                plan_id=plan_id,
                user_id=user_id,
                metadata={
                    "model": model,
                    "tokens_total": result.get('tokens_total', tokens_input + tokens_output),
                    "usage_source": "api_response"  # Mark as EXACT data from API
                }
            )
            
            logger.debug(
                f"[COST] Tracked usage for plan {plan_id}: "
                f"{provider}/{model} | "
                f"Input: {tokens_input}, Output: {tokens_output} | "
                f"Cost: ${cost_usd:.6f}"
            )
            
        except Exception as e:
            # Don't fail the main operation if cost tracking fails
            logger.warning(f"[WARN] Failed to track cost for plan {plan_id}: {e}")
    
    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get plan by ID.
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            Plan dict or None
        """
        return self.plan_repo.get_by_id(plan_id)
    
    def get_user_plans(
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
            skip: Offset
            limit: Page size
            status: Filter by status
            
        Returns:
            List of plan dicts
        """
        return self.plan_repo.get_by_user(user_id, skip, limit, status)
    
    def count_user_plans(self, user_id: str, status: Optional[PlanStatusEnum] = None) -> int:
        """
        Count user's plans.
        
        Args:
            user_id: User identifier
            status: Filter by status
            
        Returns:
            Total count
        """
        return self.plan_repo.count_by_user(user_id, status)
    
    def regenerate_plan(self, plan_id: str, user_id: str, request: PlanUpdateRequest) -> bool:
        """
        Regenerate plan with new preferences.
        
        Args:
            plan_id: Plan identifier
            user_id: User identifier (for authorization)
            request: Updated preferences
            
        Returns:
            True if regeneration started
        """
        try:
            # Get existing plan
            plan = self.plan_repo.get_by_id(plan_id)
            if not plan:
                logger.error(f"[ERROR] Plan {plan_id} not found")
                return False
            
            # Verify ownership
            if plan['user_id'] != user_id:
                logger.error(f"[ERROR] User {user_id} not authorized for plan {plan_id}")
                return False
            
            # Update preferences if provided
            update_data = {"status": PlanStatusEnum.PENDING.value}
            if request.preferences:
                # sanitizing preferences again before saving
                sanitized_preferences = sanitize_user_input(request.preferences, ["interests", "budget", "pace", "dietary"]) if isinstance(request.preferences, dict) else {}
                update_data["preferences"] = sanitized_preferences
            if request.start_date:
                update_data["start_date"] = request.start_date
            
            # Reset to PENDING (Celery will pick up)
            success = self.plan_repo.collection.update_one(
                {"plan_id": plan_id},
                {"$set": update_data}
            ).modified_count > 0
            
            if success:
                logger.info(f"[INFO] Plan {plan_id} reset to PENDING for regeneration")
            
            return success
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to regenerate plan {plan_id}: {e}")
            return False
    
    def delete_plan(self, plan_id: str, user_id: str) -> bool:
        """
        Delete plan (with authorization check).
        
        Args:
            plan_id: Plan identifier
            user_id: User identifier
            
        Returns:
            True if deleted
        """
        try:
            # Get plan
            plan = self.plan_repo.get_by_id(plan_id)
            if not plan:
                logger.warning(f"[WARN] Plan {plan_id} not found")
                return False
            
            # Verify ownership
            if plan['user_id'] != user_id:
                logger.error(f"[ERROR] User {user_id} not authorized for plan {plan_id}")
                return False
            
            # Delete
            success = self.plan_repo.delete(plan_id)
            if success:
                logger.info(f"[INFO] Deleted plan {plan_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to delete plan {plan_id}: {e}")
            return False
