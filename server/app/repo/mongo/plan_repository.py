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
from datetime import datetime, timedelta
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
        status: Optional[PlanStatusEnum] = None,
        include_deleted: bool = False,
        projection: Optional[Dict[str, int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user's plans with pagination.
        
        Args:
            user_id: User identifier
            skip: Offset for pagination
            limit: Max results per page
            status: Filter by status (optional)
            include_deleted: Include soft-deleted plans (default: False)
            projection: MongoDB projection to limit fields (optional).
                        If None, uses default projection excluding heavy fields.
            
        Returns:
            List of plan documents (newest first)
        """
        if self.collection is None:
            return []
        
        try:
            query = {"user_id": user_id}
            if not include_deleted:
                query["is_deleted"] = {"$ne": True}
            if status:
                query["status"] = status.value
            
            # Default projection excludes heavy fields for listing performance
            if projection is None:
                projection = {
                    "itinerary": 0,
                    "llm_response_raw": 0,
                    "error_message": 0,
                    "user_preferences": 0,
                }
            
            plans = list(
                self.collection.find(query, projection)
                .sort("created_at", DESCENDING)
                .skip(skip)
                .limit(limit)
            )
            
            for plan in plans:
                if '_id' in plan:
                    plan['_id'] = str(plan['_id'])
            
            logger.debug(f"[DEBUG] Found {len(plans)} plans for user {user_id}")
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
    
    def update(self, plan_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generic update method for plan fields.
        
        Args:
            plan_id: Plan identifier
            update_data: Dictionary of fields to update
            
        Returns:
            Updated plan document or None
        """
        if self.collection is None:
            return None
        
        try:
            update_data['updated_at'] = datetime.utcnow()
            
            result = self.collection.update_one(
                {"plan_id": plan_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"[INFO] Updated plan {plan_id} with {len(update_data)} fields")
                return self.get_by_id(plan_id)
            else:
                logger.warning(f"[WARN] No plan updated for {plan_id}")
                return None
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to update plan {plan_id}: {e}")
            return None
    
    def delete(self, plan_id: str) -> bool:
        """
        Soft delete plan (move to trash).
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            True if moved to trash successfully
        """
        if self.collection is None:
            return False
        
        try:
            result = self.collection.update_one(
                {"plan_id": plan_id},
                {"$set": {
                    "is_deleted": True,
                    "deleted_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }}
            )
            success = result.modified_count > 0
            
            if success:
                logger.info(f"[INFO] Moved plan to trash: {plan_id}")
            else:
                logger.warning(f"[WARN] No plan moved to trash for {plan_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to move plan to trash {plan_id}: {e}")
            return False
    
    def restore_from_trash(self, plan_id: str) -> bool:
        """
        Restore plan from trash.
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            True if restored successfully
        """
        if self.collection is None:
            return False
        
        try:
            result = self.collection.update_one(
                {"plan_id": plan_id, "is_deleted": True},
                {"$set": {
                    "is_deleted": False,
                    "deleted_at": None,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }}
            )
            success = result.modified_count > 0
            
            if success:
                logger.info(f"[INFO] Restored plan from trash: {plan_id}")
            else:
                logger.warning(f"[WARN] No plan restored from trash for {plan_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to restore plan from trash {plan_id}: {e}")
            return False
    
    def permanent_delete(self, plan_id: str) -> bool:
        """
        Permanently delete plan (mark as permanently deleted, soft delete).
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            True if permanently deleted successfully
        """
        if self.collection is None:
            return False
        
        try:
            result = self.collection.update_one(
                {"plan_id": plan_id, "is_deleted": True},
                {"$set": {
                    "is_permanently_deleted": True,
                    "updated_at": datetime.utcnow()
                }}
            )
            success = result.modified_count > 0
            
            if success:
                logger.info(f"[INFO] Permanently deleted plan: {plan_id}")
            else:
                logger.warning(f"[WARN] No plan permanently deleted for {plan_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to permanently delete plan {plan_id}: {e}")
            return False
    
    def get_trash_plans(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get user's deleted plans (trash) with BASIC INFO ONLY.
        
        Plans in trash do NOT return full itinerary details, only summary info
        for display in trash listing UI.
        
        Args:
            user_id: User identifier
            skip: Offset for pagination
            limit: Max results per page
            
        Returns:
            List of deleted plan documents with basic fields (newest first)
        """
        if self.collection is None:
            return []
        
        try:
            #delete in 30 days
            query = {
                "user_id": user_id,
                "is_deleted": True,
                "is_permanently_deleted": {"$ne": True},
                "deleted_at": {"$gte": datetime.utcnow() - timedelta(days=15)}
            }
            
            # Projection: Only return basic info, NOT full itinerary
            projection = {
                "_id": 1,
                "plan_id": 1,
                "title": 1,
                "destination": 1,
                "num_days": 1,
                "status": 1,
                "start_date": 1,
                "end_date": 1,
                "created_at": 1,
                "deleted_at": 1,
                "is_deleted": 1,
                "featured_images": 1,
                # Exclude heavy fields: itinerary, llm_response_raw, etc.
            }
            
            plans = list(
                self.collection.find(query, projection)
                .sort("deleted_at", DESCENDING)
                .skip(skip)
                .limit(limit)
            )
            
            for plan in plans:
                plan['_id'] = str(plan['_id'])
            
            logger.info(f"[INFO] Found {len(plans)} deleted plans (basic info) for user {user_id}")
            return plans
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to get trash plans for user {user_id}: {e}")
            return []
    
    def count_trash_plans(self, user_id: str) -> int:
        """
        Count user's deleted plans.
        
        Args:
            user_id: User identifier
            
        Returns:
            Total trash plan count
        """
        if self.collection is None:
            return 0
        
        try:
            query = {
                "user_id": user_id,
                "is_deleted": True,
                "is_permanently_deleted": {"$ne": True},
                "deleted_at": {"$gte": datetime.utcnow() - timedelta(days=15)}
            }
            count = self.collection.count_documents(query)
            return count
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to count trash plans for user {user_id}: {e}")
            return 0
    
    def update_sharing(
        self,
        plan_id: str,
        is_public: bool,
        share_token: Optional[str] = None
    ) -> bool:
        """
        Update plan sharing settings.
        
        Args:
            plan_id: Plan identifier
            is_public: Public visibility flag
            share_token: Share token (generated if making public)
            
        Returns:
            True if updated successfully
        """
        if self.collection is None:
            return False
        
        try:
            update_data = {
                "is_public": is_public,
                "updated_at": datetime.utcnow()
            }
            
            if is_public and share_token:
                update_data["share_token"] = share_token
            elif not is_public:
                update_data["share_token"] = None
            
            result = self.collection.update_one(
                {"plan_id": plan_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                status = "public" if is_public else "private"
                logger.info(f"[INFO] Updated plan {plan_id} sharing to {status}")
            else:
                logger.warning(f"[WARN] No plan updated for sharing {plan_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to update sharing for plan {plan_id}: {e}")
            return False
    
    def get_by_share_token(self, share_token: str) -> Optional[Dict[str, Any]]:
        """
        Get public plan by share token.
        
        Args:
            share_token: Share token
            
        Returns:
            Plan document or None
        """
        if self.collection is None:
            return None
        
        try:
            plan = self.collection.find_one({
                "share_token": share_token,
                "is_public": True,
                "is_deleted": {"$ne": True}
            })
            if plan:
                plan['_id'] = str(plan['_id'])
            return plan
        except Exception as e:
            logger.error(f"[ERROR] Failed to get plan by share token: {e}")
            return None
    
    def count_by_user(self, user_id: str, status: Optional[PlanStatusEnum] = None, include_deleted: bool = False) -> int:
        if self.collection is None:
            return 0
        try:
            query = {"user_id": user_id}
            if not include_deleted:
                query["is_deleted"] = {"$ne": True}
            if status:
                query["status"] = status.value
            return self.collection.count_documents(query)
        except Exception as e:
            logger.error(f"[ERROR] Failed to count plans for user {user_id}: {e}")
            return 0
    
    def search_by_user(
        self,
        user_id: str,
        query: str = "",
        limit: int = 20,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Plan]:
        if self.collection is None:
            return []
        try:
            mongo_query = {"user_id": user_id}
            if not include_deleted:
                mongo_query["is_deleted"] = {"$ne": True}
            if query:
                mongo_query["$or"] = [
                    {"title": {"$regex": query, "$options": "i"}},
                    {"destination": {"$regex": query, "$options": "i"}}
                ]
            docs = list(
                self.collection.find(mongo_query)
                .sort("created_at", DESCENDING)
                .skip(offset)
                .limit(limit)
            )
            plans = []
            for doc in docs:
                doc['_id'] = str(doc['_id'])
                try:
                    plans.append(Plan(**doc))
                except Exception:
                    pass
            return plans
        except Exception as e:
            logger.error(f"[ERROR] Failed to search plans for user {user_id}: {e}")
            return []
