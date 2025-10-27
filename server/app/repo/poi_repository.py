"""
POI Repository - MongoDB Data Access Layer
===========================================

Purpose:
- CRUD operations for POI collection
- Deduplication checking
- Geo-spatial queries
- Text search (fallback if no Elasticsearch)

Author: Travel Agent P Team
Date: October 27, 2025
"""

from typing import List, Optional, Dict, Any
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError
from pymongo import GEOSPHERE, TEXT, DESCENDING
import logging
from datetime import datetime

from app.core.mongodb_client import get_mongodb_client
from app.model.poi import POI, POISearchRequest, CategoryEnum, PriceLevelEnum
from app.utils.poi_dedupe import (
    generate_dedupe_key,
    normalize_poi_name,
    are_pois_duplicate
)

logger = logging.getLogger(__name__)


class POIRepository:
    """
    Repository for POI (Point of Interest) data access.
    
    Features:
    - CRUD operations with validation
    - Deduplication (strict + fuzzy)
    - Geo-spatial search (2dsphere)
    - Text search
    - Category/price filtering
    - Pagination
    """
    
    def __init__(self):
        """Initialize POI repository."""
        self.client = get_mongodb_client()
        self.collection: Optional[Collection] = None
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Ensure POI collection exists and get reference."""
        db = self.client.get_database()
        if db is not None:
            collection_name = "poi"
            self.collection = db[collection_name]
            logger.info(f"✅ POI collection ready: {collection_name}")
        else:
            logger.error("❌ Failed to get database for POI repository")
    
    def create(self, poi: POI) -> Dict[str, Any]:
        """
        Create new POI with deduplication check.
        
        Args:
            poi: POI model instance
            
        Returns:
            Created POI document
            
        Raises:
            DuplicateKeyError: If dedupe_key already exists
            ValueError: If fuzzy duplicate found
            
        Example:
            poi = POI(name="Mỹ Khê Beach", location={...}, ...)
            result = poi_repo.create(poi)
            print(f"Created POI: {result['poi_id']}")
        """
        if self.collection is None:
            raise RuntimeError("POI collection not available")
        
        try:
            # Convert Pydantic model to dict
            poi_dict = poi.model_dump(mode='json', exclude_none=False)
            
            # Generate dedupe_key if not provided
            if not poi_dict.get('dedupe_key'):
                lng, lat = poi_dict['location']['coordinates']
                poi_dict['dedupe_key'] = generate_dedupe_key(
                    name=poi_dict['name'],
                    lat=lat,
                    lng=lng
                )
            
            # Generate poi_id if not provided
            if not poi_dict.get('poi_id'):
                poi_dict['poi_id'] = f"poi_{poi_dict['dedupe_key']}"
            
            # Check for fuzzy duplicates (optional, can be disabled for performance)
            fuzzy_duplicate = self._find_fuzzy_duplicate(poi_dict)
            if fuzzy_duplicate:
                logger.warning(f"⚠️ Fuzzy duplicate found: {fuzzy_duplicate['poi_id']}")
                raise ValueError(
                    f"Similar POI already exists: {fuzzy_duplicate['poi_id']} "
                    f"(name: {fuzzy_duplicate['name']}, distance: <150m)"
                )
            
            # Insert into MongoDB
            result = self.collection.insert_one(poi_dict)
            
            logger.info(f"✅ Created POI: {poi_dict['poi_id']}")
            
            # Return created document
            created_poi = self.collection.find_one({"_id": result.inserted_id})
            return created_poi
        
        except DuplicateKeyError as e:
            logger.error(f"❌ Duplicate POI: {poi.dedupe_key}")
            # Find existing POI with same dedupe_key
            existing = self.collection.find_one({"dedupe_key": poi.dedupe_key})
            if existing:
                raise ValueError(
                    f"Duplicate POI: {existing['poi_id']} "
                    f"(name: {existing['name']}, dedupe_key: {poi.dedupe_key})"
                )
            raise
        
        except Exception as e:
            logger.error(f"❌ Failed to create POI: {e}")
            raise
    
    def _find_fuzzy_duplicate(self, poi_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find fuzzy duplicates using name similarity and distance.
        
        Args:
            poi_dict: POI document
            
        Returns:
            Duplicate POI if found, None otherwise
        """
        if self.collection is None:
            return None
        
        try:
            lng, lat = poi_dict['location']['coordinates']
            
            # Find nearby POI (within 500m for fuzzy check)
            nearby_poi = self.collection.find({
                "location": {
                    "$nearSphere": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": [lng, lat]
                        },
                        "$maxDistance": 500  # 500 meters
                    }
                }
            }).limit(10)
            
            # Check each nearby POI for fuzzy duplicate
            for existing in nearby_poi:
                if are_pois_duplicate(poi_dict, existing):
                    return existing
            
            return None
        
        except Exception as e:
            logger.warning(f"⚠️ Fuzzy duplicate check failed: {e}")
            return None
    
    def get_by_id(self, poi_id: str) -> Optional[Dict[str, Any]]:
        """
        Get POI by ID.
        
        Args:
            poi_id: POI identifier
            
        Returns:
            POI document if found, None otherwise
            
        Example:
            poi = poi_repo.get_by_id("poi_mykhebeach")
            if poi:
                print(f"Found: {poi['name']}")
        """
        if self.collection is None:
            return None
        
        try:
            poi = self.collection.find_one({"poi_id": poi_id})
            
            if poi:
                # Increment view count
                self.collection.update_one(
                    {"poi_id": poi_id},
                    {"$inc": {"metadata.view_count": 1}}
                )
            
            return poi
        
        except Exception as e:
            logger.error(f"❌ Failed to get POI {poi_id}: {e}")
            return None
    
    def update(self, poi_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update POI by ID.
        
        Args:
            poi_id: POI identifier
            updates: Fields to update
            
        Returns:
            Updated POI document if found, None otherwise
            
        Example:
            updates = {"ratings.average": 4.8, "ratings.count": 1000}
            poi = poi_repo.update("poi_mykhebeach", updates)
        """
        if self.collection is None:
            return None
        
        try:
            # Add updated_at timestamp
            updates["metadata.updated_at"] = datetime.utcnow()
            
            result = self.collection.find_one_and_update(
                {"poi_id": poi_id},
                {"$set": updates},
                return_document=True
            )
            
            if result:
                logger.info(f"✅ Updated POI: {poi_id}")
            else:
                logger.warning(f"⚠️ POI not found: {poi_id}")
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Failed to update POI {poi_id}: {e}")
            return None
    
    def delete(self, poi_id: str) -> bool:
        """
        Delete POI by ID.
        
        Args:
            poi_id: POI identifier
            
        Returns:
            True if deleted, False otherwise
            
        Example:
            success = poi_repo.delete("poi_old_entry")
        """
        if self.collection is None:
            return False
        
        try:
            result = self.collection.delete_one({"poi_id": poi_id})
            
            if result.deleted_count > 0:
                logger.info(f"✅ Deleted POI: {poi_id}")
                return True
            else:
                logger.warning(f"⚠️ POI not found: {poi_id}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Failed to delete POI {poi_id}: {e}")
            return False
    
    def search(self, search_request: POISearchRequest) -> Dict[str, Any]:
        """
        Search POI with filters and pagination.
        
        Supports:
        - Text search (name, description)
        - Geo-spatial search (lat/lng/radius)
        - Category filter
        - Price level filter
        - Min rating filter
        - Sorting by relevance, popularity, rating
        
        Args:
            search_request: Search parameters
            
        Returns:
            {
                "results": [POI documents],
                "total": total count,
                "page": current page,
                "limit": items per page,
                "total_pages": total pages
            }
            
        Example:
            search = POISearchRequest(
                q="beach",
                lat=16.0544,
                lng=108.2428,
                radius=10,
                categories=["beach"],
                min_rating=4.0,
                page=1,
                limit=20
            )
            results = poi_repo.search(search)
        """
        if self.collection is None:
            return {
                "results": [],
                "total": 0,
                "page": search_request.page,
                "limit": search_request.limit,
                "total_pages": 0
            }
        
        try:
            # Build query pipeline
            pipeline = []
            match_stage = {}
            
            # Geo-spatial search (highest priority)
            if search_request.lat and search_request.lng and search_request.radius:
                lng = search_request.lng
                lat = search_request.lat
                radius_meters = search_request.radius * 1000  # Convert km to meters
                
                pipeline.append({
                    "$geoNear": {
                        "near": {
                            "type": "Point",
                            "coordinates": [lng, lat]
                        },
                        "distanceField": "distance_m",
                        "maxDistance": radius_meters,
                        "spherical": True
                    }
                })
                
                # Add distance_km field
                pipeline.append({
                    "$addFields": {
                        "distance_km": {"$divide": ["$distance_m", 1000]}
                    }
                })
            
            # Text search
            if search_request.q:
                match_stage["$text"] = {"$search": search_request.q}
            
            # Category filter
            if search_request.categories:
                match_stage["categories"] = {"$in": search_request.categories}
            
            # Price level filter
            if search_request.price_level:
                match_stage["pricing.level"] = search_request.price_level
            
            # Min rating filter
            if search_request.min_rating:
                match_stage["ratings.average"] = {"$gte": search_request.min_rating}
            
            # Add match stage if filters exist
            if match_stage:
                pipeline.append({"$match": match_stage})
            
            # Add text search score (if text search)
            if search_request.q:
                pipeline.append({
                    "$addFields": {
                        "search_score": {"$meta": "textScore"}
                    }
                })
            
            # Count total results
            count_pipeline = pipeline.copy()
            count_pipeline.append({"$count": "total"})
            count_result = list(self.collection.aggregate(count_pipeline))
            total = count_result[0]["total"] if count_result else 0
            
            # Sorting
            sort_stage = {}
            if search_request.q:
                sort_stage["search_score"] = -1
            elif search_request.lat and search_request.lng:
                sort_stage["distance_km"] = 1
            else:
                sort_stage["metadata.popularity_score"] = -1
                sort_stage["ratings.average"] = -1
            
            pipeline.append({"$sort": sort_stage})
            
            # Pagination
            skip = (search_request.page - 1) * search_request.limit
            pipeline.append({"$skip": skip})
            pipeline.append({"$limit": search_request.limit})
            
            # Execute query
            results = list(self.collection.aggregate(pipeline))
            
            # Calculate total pages
            total_pages = (total + search_request.limit - 1) // search_request.limit
            
            logger.info(f"✅ Search completed: {len(results)} results (total: {total})")
            
            return {
                "results": results,
                "total": total,
                "page": search_request.page,
                "limit": search_request.limit,
                "total_pages": total_pages
            }
        
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return {
                "results": [],
                "total": 0,
                "page": search_request.page,
                "limit": search_request.limit,
                "total_pages": 0
            }
    
    def get_by_category(self, category: CategoryEnum, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get POI by category.
        
        Args:
            category: Category to filter by
            limit: Max results
            
        Returns:
            List of POI documents
            
        Example:
            beaches = poi_repo.get_by_category(CategoryEnum.BEACH, limit=10)
        """
        if self.collection is None:
            return []
        
        try:
            results = self.collection.find(
                {"categories": category}
            ).sort([
                ("metadata.popularity_score", DESCENDING),
                ("ratings.average", DESCENDING)
            ]).limit(limit)
            
            return list(results)
        
        except Exception as e:
            logger.error(f"❌ Get by category failed: {e}")
            return []
    
    def get_nearby(self, lat: float, lng: float, radius_km: float = 10, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get nearby POI within radius.
        
        Args:
            lat: Latitude
            lng: Longitude
            radius_km: Search radius in km
            limit: Max results
            
        Returns:
            List of POI documents with distance_km field
            
        Example:
            nearby = poi_repo.get_nearby(lat=16.0544, lng=108.2428, radius_km=5)
        """
        if self.collection is None:
            return []
        
        try:
            radius_meters = radius_km * 1000
            
            pipeline = [
                {
                    "$geoNear": {
                        "near": {
                            "type": "Point",
                            "coordinates": [lng, lat]
                        },
                        "distanceField": "distance_m",
                        "maxDistance": radius_meters,
                        "spherical": True
                    }
                },
                {
                    "$addFields": {
                        "distance_km": {"$divide": ["$distance_m", 1000]}
                    }
                },
                {"$limit": limit}
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            logger.info(f"✅ Found {len(results)} nearby POI")
            
            return results
        
        except Exception as e:
            logger.error(f"❌ Get nearby failed: {e}")
            return []
    
    def get_popular(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get popular POI sorted by popularity score and ratings.
        
        Args:
            limit: Max results
            
        Returns:
            List of POI documents
            
        Example:
            popular = poi_repo.get_popular(limit=10)
        """
        if self.collection is None:
            return []
        
        try:
            results = self.collection.find().sort([
                ("metadata.popularity_score", DESCENDING),
                ("ratings.average", DESCENDING),
                ("ratings.count", DESCENDING)
            ]).limit(limit)
            
            return list(results)
        
        except Exception as e:
            logger.error(f"❌ Get popular failed: {e}")
            return []
    
    def count(self) -> int:
        """
        Get total POI count.
        
        Returns:
            Total number of POI
            
        Example:
            total = poi_repo.count()
            print(f"Total POI: {total}")
        """
        if self.collection is None:
            return 0
        
        try:
            return self.collection.count_documents({})
        except Exception as e:
            logger.error(f"❌ Count failed: {e}")
            return 0
