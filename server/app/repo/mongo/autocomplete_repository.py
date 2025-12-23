"""
Autocomplete Cache Repository - MongoDB Data Access Layer
==========================================================

Purpose:
- CRUD operations for autocomplete_cache collection
- Text search fallback (when ES is down)
- Click count and status management
- Persistent storage for Google Places predictions

Author: Travel Agent P Team
Date: December 22, 2025
"""

from typing import List, Optional, Dict, Any
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, BulkWriteError
from pymongo import TEXT, DESCENDING
import logging
from datetime import datetime

from ...core.clients.mongodb_client import get_mongodb_client
from ...model.mongo.autocomplete_cache import AutocompleteItem, CacheStatus
from .interfaces import AutocompleteRepositoryInterface

logger = logging.getLogger(__name__)


class AutocompleteRepository(AutocompleteRepositoryInterface):
    """
    Repository for Autocomplete Cache data access.
    
    Collection: autocomplete_cache
    
    Features:
    - CRUD operations with upsert
    - Text search (fallback when ES is down)
    - Click count tracking (popularity)
    - Status management (pending → cached)
    - Bulk operations for efficiency
    
    Indexes:
    - place_id: unique
    - main_text_unaccented: text
    - click_count: -1 (descending)
    - status: 1
    - types: 1
    - terms: 1
    """
    
    COLLECTION_NAME = "autocomplete_cache"
    
    def __init__(self):
        """Initialize Autocomplete repository."""
        self.client = get_mongodb_client()
        self.collection: Optional[Collection] = None
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Ensure autocomplete_cache collection exists with indexes."""
        db = self.client.get_database()
        if db is not None:
            self.collection = db[self.COLLECTION_NAME]
            self._ensure_indexes()
            logger.info(f"[INFO] Autocomplete cache collection ready: {self.COLLECTION_NAME}")
        else:
            logger.error("[ERROR] Failed to get database for Autocomplete repository")
    
    def _ensure_indexes(self):
        """Create indexes if not exist."""
        if self.collection is None:
            return
        
        try:
            existing_indexes = [idx["name"] for idx in self.collection.list_indexes()]
            
            # Unique index on place_id
            if "place_id_unique" not in existing_indexes:
                self.collection.create_index(
                    "place_id",
                    unique=True,
                    name="place_id_unique"
                )
                logger.info("[INFO] Created unique index on place_id")
            
            # Text index for search fallback
            if "main_text_unaccented_text" not in existing_indexes:
                self.collection.create_index(
                    [("main_text_unaccented", TEXT)],
                    name="main_text_unaccented_text"
                )
                logger.info("[INFO] Created text index on main_text_unaccented")
            
            # Click count for popularity sorting
            if "click_count_desc" not in existing_indexes:
                self.collection.create_index(
                    [("click_count", DESCENDING)],
                    name="click_count_desc"
                )
                logger.info("[INFO] Created index on click_count")
            
            # Status for filtering
            if "status_1" not in existing_indexes:
                self.collection.create_index("status", name="status_1")
                logger.info("[INFO] Created index on status")
            
            # Types for filtering by place type
            if "types_1" not in existing_indexes:
                self.collection.create_index("types", name="types_1")
                logger.info("[INFO] Created index on types")
            
            # Terms for filtering by location hierarchy
            if "terms_1" not in existing_indexes:
                self.collection.create_index("terms", name="terms_1")
                logger.info("[INFO] Created index on terms")
                
        except Exception as e:
            logger.warning(f"[WARN] Failed to create indexes: {e}")
    
    def create(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new autocomplete cache item.
        
        Args:
            item: AutocompleteItem as dict
            
        Returns:
            Created document
            
        Raises:
            DuplicateKeyError: If place_id already exists
        """
        if self.collection is None:
            raise RuntimeError("Autocomplete collection not available")
        
        try:
            # Add timestamps if not present
            now = datetime.utcnow()
            if "created_at" not in item:
                item["created_at"] = now
            if "updated_at" not in item:
                item["updated_at"] = now
            
            result = self.collection.insert_one(item)
            item["_id"] = result.inserted_id
            
            logger.debug(f"[DEBUG] Created autocomplete item: {item.get('place_id')}")
            return item
            
        except DuplicateKeyError:
            logger.warning(f"[WARN] Duplicate place_id: {item.get('place_id')}")
            raise
    
    def bulk_create(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Bulk create autocomplete cache items.
        Uses ordered=False to continue on duplicates.
        
        Args:
            items: List of AutocompleteItem dicts
            
        Returns:
            {"inserted": count, "skipped": count}
        """
        if self.collection is None:
            raise RuntimeError("Autocomplete collection not available")
        
        if not items:
            return {"inserted": 0, "skipped": 0}
        
        # Add timestamps
        now = datetime.utcnow()
        for item in items:
            if "created_at" not in item:
                item["created_at"] = now
            if "updated_at" not in item:
                item["updated_at"] = now
        
        try:
            result = self.collection.insert_many(items, ordered=False)
            inserted = len(result.inserted_ids)
            skipped = len(items) - inserted
            
            logger.info(f"[INFO] Bulk created: {inserted} inserted, {skipped} skipped")
            return {"inserted": inserted, "skipped": skipped}
            
        except BulkWriteError as bwe:
            inserted = bwe.details.get("nInserted", 0)
            skipped = len(items) - inserted
            
            logger.info(f"[INFO] Bulk created with duplicates: {inserted} inserted, {skipped} skipped")
            return {"inserted": inserted, "skipped": skipped}
    
    def upsert(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upsert (insert or update) autocomplete cache item.
        
        Args:
            item: AutocompleteItem as dict
            
        Returns:
            Upserted document
        """
        if self.collection is None:
            raise RuntimeError("Autocomplete collection not available")
        
        place_id = item.get("place_id")
        if not place_id:
            raise ValueError("place_id is required for upsert")
        
        # Set timestamps
        now = datetime.utcnow()
        
        # Create a copy for $set, excluding created_at to avoid conflict
        set_data = {k: v for k, v in item.items() if k != "created_at"}
        set_data["updated_at"] = now
        
        # Use $setOnInsert for created_at
        result = self.collection.update_one(
            {"place_id": place_id},
            {
                "$set": set_data,
                "$setOnInsert": {"created_at": now}
            },
            upsert=True
        )
        
        if result.upserted_id:
            logger.debug(f"[DEBUG] Inserted autocomplete item: {place_id}")
        else:
            logger.debug(f"[DEBUG] Updated autocomplete item: {place_id}")
        
        return item
    
    def get_by_place_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get autocomplete item by place_id.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            Document if found, None otherwise
        """
        if self.collection is None:
            return None
        
        return self.collection.find_one({"place_id": place_id})
    
    def search(
        self,
        query: str,
        limit: int = 10,
        types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Text search for autocomplete (fallback when ES is down).
        
        Uses MongoDB text search on main_text_unaccented.
        Falls back to regex if text search fails.
        
        Args:
            query: Search query
            limit: Maximum results
            types: Filter by place types
            
        Returns:
            List of matching documents
        """
        if self.collection is None:
            return []
        
        if not query or not query.strip():
            return []
        
        query = query.strip()
        
        try:
            # Build filter
            filter_query: Dict[str, Any] = {
                "$text": {"$search": query}
            }
            
            if types:
                filter_query["types"] = {"$in": types}
            
            # Text search with score
            results = list(
                self.collection.find(
                    filter_query,
                    {"score": {"$meta": "textScore"}}
                )
                .sort([
                    ("score", {"$meta": "textScore"}),
                    ("click_count", DESCENDING)
                ])
                .limit(limit)
            )
            
            logger.debug(f"[DEBUG] MongoDB text search '{query}': {len(results)} results")
            return results
            
        except Exception as e:
            logger.warning(f"[WARN] Text search failed, falling back to regex: {e}")
            
            # Fallback to regex (slower but works)
            filter_query = {
                "main_text_unaccented": {
                    "$regex": f"^{query.lower()}",
                    "$options": "i"
                }
            }
            
            if types:
                filter_query["types"] = {"$in": types}
            
            results = list(
                self.collection.find(filter_query)
                .sort([("click_count", DESCENDING)])
                .limit(limit)
            )
            
            return results
    
    def update_status(
        self,
        place_id: str,
        status: str,
        lat: Optional[float] = None,
        lng: Optional[float] = None
    ) -> bool:
        """
        Update status from pending to cached.
        
        Args:
            place_id: Google Place ID
            status: New status ("cached" or "pending")
            lat: Latitude (optional, set when resolving)
            lng: Longitude (optional, set when resolving)
            
        Returns:
            True if updated, False if not found
        """
        if self.collection is None:
            return False
        
        update_doc: Dict[str, Any] = {
            "$set": {
                "status": status,
                "updated_at": datetime.utcnow()
            }
        }
        
        # Add coordinates if provided
        if lat is not None:
            update_doc["$set"]["lat"] = lat
        if lng is not None:
            update_doc["$set"]["lng"] = lng
        
        result = self.collection.update_one(
            {"place_id": place_id},
            update_doc
        )
        
        if result.modified_count > 0:
            logger.debug(f"[DEBUG] Updated status for {place_id} to {status}")
            return True
        
        return False
    
    def increment_click(self, place_id: str) -> bool:
        """
        Increment click_count for popularity tracking.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            True if updated, False if not found
        """
        if self.collection is None:
            return False
        
        result = self.collection.update_one(
            {"place_id": place_id},
            {
                "$inc": {"click_count": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            logger.debug(f"[DEBUG] Incremented click for {place_id}")
            return True
        
        return False
    
    def delete_by_place_id(self, place_id: str) -> bool:
        """
        Delete autocomplete item by place_id.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            True if deleted, False if not found
        """
        if self.collection is None:
            return False
        
        result = self.collection.delete_one({"place_id": place_id})
        
        if result.deleted_count > 0:
            logger.debug(f"[DEBUG] Deleted autocomplete item: {place_id}")
            return True
        
        return False
    
    def count(self, status: Optional[str] = None) -> int:
        """
        Count documents in collection.
        
        Args:
            status: Optional filter by status
            
        Returns:
            Document count
        """
        if self.collection is None:
            return 0
        
        filter_query = {}
        if status:
            filter_query["status"] = status
        
        return self.collection.count_documents(filter_query)
    
    def get_popular(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get most popular autocomplete items by click_count.
        
        Args:
            limit: Maximum results
            
        Returns:
            List of popular items sorted by click_count desc
        """
        if self.collection is None:
            return []
        
        return list(
            self.collection.find({"click_count": {"$gt": 0}})
            .sort([("click_count", DESCENDING)])
            .limit(limit)
        )
    
    def get_pending(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get pending items that need to be resolved.
        
        Args:
            limit: Maximum results
            
        Returns:
            List of pending items
        """
        if self.collection is None:
            return []
        
        return list(
            self.collection.find({"status": CacheStatus.PENDING.value})
            .sort([("click_count", DESCENDING)])
            .limit(limit)
        )
    
    def delete_all(self) -> int:
        """
        Delete all documents (for testing/reset).
        
        Returns:
            Number of deleted documents
        """
        if self.collection is None:
            return 0
        
        result = self.collection.delete_many({})
        logger.warning(f"[WARN] Deleted all {result.deleted_count} autocomplete items")
        return result.deleted_count
