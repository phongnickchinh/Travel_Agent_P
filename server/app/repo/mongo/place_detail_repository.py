"""
Place Detail Repository - MongoDB Data Access Layer
====================================================

Purpose:
- CRUD operations for place_details collection
- Cache place details from Google Places API
- Separate from autocomplete_cache (predictions) and poi (attractions)

Author: Travel Agent P Team
Date: December 24, 2025
"""

from typing import List, Optional, Dict, Any
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError
from pymongo import DESCENDING
import logging
from datetime import datetime

from ...core.clients.mongodb_client import get_mongodb_client
from ...model.mongo.place_detail import PlaceDetail
from .interfaces.place_detail_repository_interface import PlaceDetailRepositoryInterface

logger = logging.getLogger(__name__)


class PlaceDetailRepository(PlaceDetailRepositoryInterface):
    """
    Repository for Place Detail data access.
    
    Collection: place_details
    
    Features:
    - Get by place_id (cached lookup)
    - Upsert (create or update)
    - Increment access count
    - Bulk operations
    
    Indexes:
    - place_id: unique
    - access_count: -1 (descending for popularity)
    - types: 1 (for filtering by place type)
    """
    
    COLLECTION_NAME = "place_details"
    
    def __init__(self):
        """Initialize Place Detail repository."""
        self.client = get_mongodb_client()
        self.collection: Optional[Collection] = None
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Ensure place_details collection exists.
        
        Note: Indexes are created centrally by mongodb_client.py on startup.
        Do NOT create indexes here to avoid naming conflicts.
        """
        db = self.client.get_database()
        if db is not None:
            self.collection = db[self.COLLECTION_NAME]
            logger.debug("PlaceDetail collection ready: %s", self.COLLECTION_NAME)
        else:
            logger.error("[ERROR] Failed to get database for PlaceDetail repository")
    
    def get_by_place_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get place detail by place_id.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            PlaceDetail dict or None
        """
        if self.collection is None:
            return None
        
        try:
            doc = self.collection.find_one({"place_id": place_id})
            if doc:
                # Increment access count
                self.collection.update_one(
                    {"place_id": place_id},
                    {
                        "$inc": {"access_count": 1},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
                # Remove MongoDB _id
                doc.pop("_id", None)
                logger.debug(f"[CACHE HIT] PlaceDetail: {place_id}")
                return doc
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to get place detail {place_id}: {e}")
            return None
    
    def upsert(self, place_detail: PlaceDetail) -> bool:
        """
        Create or update place detail.
        
        Args:
            place_detail: PlaceDetail model instance
            
        Returns:
            True if successful
        """
        if self.collection is None:
            return False
        
        try:
            data = place_detail.to_dict()
            
            # Remove created_at from data to avoid conflict with $setOnInsert
            # (created_at should only be set on insert, not on update)
            data.pop("created_at", None)
            
            # Always update updated_at
            data["updated_at"] = datetime.utcnow()
            
            result = self.collection.update_one(
                {"place_id": place_detail.place_id},
                {
                    "$set": data,
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"[INFO] Created new PlaceDetail: {place_detail.place_id}")
            else:
                logger.debug(f"[INFO] Updated PlaceDetail: {place_detail.place_id}")
            
            return True
            
        except DuplicateKeyError:
            logger.warning(f"[WARNING] Duplicate place_id: {place_detail.place_id}")
            return False
        except Exception as e:
            logger.error(f"[ERROR] Failed to upsert place detail: {e}")
            return False
    
    def upsert_from_dict(self, place_data: Dict[str, Any]) -> bool:
        """
        Create or update place detail from dict (raw API response).
        
        Args:
            place_data: Dict with place detail data
            
        Returns:
            True if successful
        """
        try:
            place_detail = PlaceDetail.from_google_response(place_data)
            return self.upsert(place_detail)
        except Exception as e:
            logger.error(f"[ERROR] Failed to create PlaceDetail from dict: {e}")
            return False
    
    def exists(self, place_id: str) -> bool:
        """
        Check if place detail exists in cache.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            True if exists
        """
        if self.collection is None:
            return False
        
        try:
            return self.collection.count_documents({"place_id": place_id}, limit=1) > 0
        except Exception as e:
            logger.error(f"[ERROR] Failed to check existence: {e}")
            return False
    
    def get_popular(self, limit: int = 10, types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get popular places by access count.
        
        Args:
            limit: Maximum results
            types: Filter by place types
            
        Returns:
            List of PlaceDetail dicts
        """
        if self.collection is None:
            return []
        
        try:
            query = {}
            if types:
                query["types"] = {"$in": types}
            
            cursor = self.collection.find(query).sort(
                "access_count", DESCENDING
            ).limit(limit)
            
            results = []
            for doc in cursor:
                doc.pop("_id", None)
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to get popular places: {e}")
            return []
    
    def delete(self, place_id: str) -> bool:
        """
        Delete place detail by place_id.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            True if deleted
        """
        if self.collection is None:
            return False
        
        try:
            result = self.collection.delete_one({"place_id": place_id})
            if result.deleted_count > 0:
                logger.info(f"[INFO] Deleted PlaceDetail: {place_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to delete place detail: {e}")
            return False
    
    def find_by_type(self, place_type: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Find place details by type.
        
        Args:
            place_type: Place type (e.g., 'locality', 'country', 'administrative_area')
            limit: Maximum results to return
            
        Returns:
            List of PlaceDetail dicts matching the type
        """
        if self.collection is None:
            return []
        
        try:
            query = {"types": place_type}
            
            cursor = self.collection.find(query).sort(
                "access_count", DESCENDING
            ).limit(limit)
            
            results = []
            for doc in cursor:
                doc.pop("_id", None)
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to find places by type {place_type}: {e}")
            return []
    
    def bulk_upsert(self, place_details: List[PlaceDetail]) -> Dict[str, int]:
        """
        Bulk upsert place details.
        
        Args:
            place_details: List of PlaceDetail model instances
            
        Returns:
            Dict with counts: {'inserted': int, 'updated': int, 'failed': int}
        """
        if self.collection is None:
            return {'inserted': 0, 'updated': 0, 'failed': 0}
        
        counts = {'inserted': 0, 'updated': 0, 'failed': 0}
        
        for place_detail in place_details:
            try:
                data = place_detail.to_dict()
                data["updated_at"] = datetime.utcnow()
                
                result = self.collection.update_one(
                    {"place_id": place_detail.place_id},
                    {"$set": data, "$setOnInsert": {"created_at": datetime.utcnow()}},
                    upsert=True
                )
                
                if result.upserted_id:
                    counts['inserted'] += 1
                else:
                    counts['updated'] += 1
                    
            except Exception as e:
                logger.error(f"[ERROR] Failed to upsert {place_detail.place_id}: {e}")
                counts['failed'] += 1
        
        logger.info(
            f"[BULK] PlaceDetail upsert complete: "
            f"inserted={counts['inserted']}, updated={counts['updated']}, failed={counts['failed']}"
        )
        
        return counts
    
    def count(self) -> int:
        """Get total count of place details."""
        if self.collection is None:
            return 0
        
        try:
            return self.collection.count_documents({})
        except Exception as e:
            logger.error(f"[ERROR] Failed to count place details: {e}")
            return 0
