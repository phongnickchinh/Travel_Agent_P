"""
Plan Repository - MongoDB Data Access Layer
============================================

Purpose:
- CRUD operations for travel plans
- Query by user, status, destination
- Update plan status during LLM generation
- Pagination support

Author: Travel Agent P Team
Date: Week 4 - HuggingFace + LangChain Integration
"""

from typing import List, Optional, Dict, Any
from pymongo.collection import Collection
from pymongo import DESCENDING
import logging
from datetime import datetime
import secrets

from ...core.clients.mongodb_client import get_mongodb_client
from ...model.mongo.plan import Plan, PlanStatusEnum
from .interfaces import PlanRepositoryInterface

logger = logging.getLogger(__name__)


class PlanRepository(PlanRepositoryInterface):
    """
    Repository for travel plan data access.
    
    Features:
    - Create plan (with auto-generated plan_id)
    - Get by plan_id or user_id
    - Update status (PENDING → PROCESSING → COMPLETED/FAILED)
    - Update itinerary when LLM completes
    - List user's plans with pagination
    """
    
    def __init__(self):
        """Initialize Plan repository."""
        self.client = get_mongodb_client()
        self.collection: Optional[Collection] = None
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Ensure plan collection exists and create indexes."""
        db = self.client.get_database()
        if db is not None:
            collection_name = "plan"
            self.collection = db[collection_name]
            
            # Create indexes
            try:
                self.collection.create_index("plan_id", unique=True)
                self.collection.create_index("user_id")
                self.collection.create_index([("user_id", DESCENDING), ("created_at", DESCENDING)])
                self.collection.create_index("status")
                logger.info(f"[INFO] Plan collection ready with indexes: {collection_name}")
            except Exception as e:
                logger.warning(f"[WARN] Failed to create indexes: {e}")
        else:
            logger.error("[ERROR] Failed to get database for Plan repository")
    
    def create(self, plan: Plan) -> Dict[str, Any]:
        """
        Create new plan with auto-generated plan_id.
        
        Args:
            plan: Plan model instance
            
        Returns:
            Created plan document
            
        Example:
            plan = Plan(user_id="user123", destination="Da Nang", num_days=3)
            result = plan_repo.create(plan)
            print(f"Created plan: {result['plan_id']}")
        """
        if self.collection is None:
            raise RuntimeError("Plan collection not available")
        
        try:
            plan_dict = plan.model_dump(mode='json', exclude_none=False)
            
            # Generate plan_id if not provided
            if not plan_dict.get('plan_id'):
                plan_dict['plan_id'] = f"plan_{secrets.token_urlsafe(12)}"
            
            # Set timestamps
            now = datetime.utcnow()
            plan_dict['created_at'] = now
            plan_dict['updated_at'] = now
            
            # Insert to MongoDB
            result = self.collection.insert_one(plan_dict)
            plan_dict['_id'] = str(result.inserted_id)
            
            logger.info(f"[INFO] Created plan: {plan_dict['plan_id']} for user: {plan_dict['user_id']}")
            return plan_dict
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to create plan: {e}")
            raise
    
    def get_by_id(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get plan by plan_id.
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            Plan document or None
        """
        if self.collection is None:
            return None
        
        try:
            plan = self.collection.find_one({"plan_id": plan_id})
            if plan:
                plan['_id'] = str(plan['_id'])
            return plan
        except Exception as e:
            logger.error(f"[ERROR] Failed to get plan {plan_id}: {e}")
            return None
    
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
        if self.collection is None:
            return []
        
        try:
            query = {"user_id": user_id}
            if status:
                query["status"] = status.value
            
            plans = list(
                self.collection.find(query)
                .sort("created_at", DESCENDING)
                .skip(skip)
                .limit(limit)
            )
            
            for plan in plans:
                plan['_id'] = str(plan['_id'])
            
            logger.info(f"[INFO] Found {len(plans)} plans for user {user_id}")
            return plans
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to get plans for user {user_id}: {e}")
            return []
    
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
        if self.collection is None:
            return False
        
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow()
            }
            
            if error_message:
                update_data["error_message"] = error_message
            
            result = self.collection.update_one(
                {"plan_id": plan_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"[INFO] Updated plan {plan_id} to status: {status.value}")
            else:
                logger.warning(f"[WARN] No plan updated for {plan_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to update status for plan {plan_id}: {e}")
            return False
    
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
        if self.collection is None:
            return False
        
        try:
            # Calculate total_pois
            total_pois = sum(len(day.get('poi_ids', [])) for day in itinerary)
            
            update_data = {
                "itinerary": itinerary,
                "status": PlanStatusEnum.COMPLETED.value,
                "llm_model": llm_model,
                "total_pois": total_pois,
                "updated_at": datetime.utcnow()
            }
            
            if llm_response_raw:
                update_data["llm_response_raw"] = llm_response_raw
            
            if metadata:
                update_data["metadata"] = metadata
            
            result = self.collection.update_one(
                {"plan_id": plan_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"[INFO] Updated itinerary for plan {plan_id} ({total_pois} POIs)")
            else:
                logger.warning(f"[WARN] No itinerary updated for {plan_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to update itinerary for plan {plan_id}: {e}")
            return False
    
    def delete(self, plan_id: str) -> bool:
        """
        Delete plan by plan_id.
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            True if deleted successfully
        """
        if self.collection is None:
            return False
        
        try:
            result = self.collection.delete_one({"plan_id": plan_id})
            success = result.deleted_count > 0
            
            if success:
                logger.info(f"[INFO] Deleted plan: {plan_id}")
            else:
                logger.warning(f"[WARN] No plan deleted for {plan_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to delete plan {plan_id}: {e}")
            return False
    
    def count_by_user(self, user_id: str, status: Optional[PlanStatusEnum] = None) -> int:
        """
        Count user's plans.
        
        Args:
            user_id: User identifier
            status: Filter by status (optional)
            
        Returns:
            Total plan count
        """
        if self.collection is None:
            return 0
        
        try:
            query = {"user_id": user_id}
            if status:
                query["status"] = status.value
            
            count = self.collection.count_documents(query)
            return count
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to count plans for user {user_id}: {e}")
            return 0
