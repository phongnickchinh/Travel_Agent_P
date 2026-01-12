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

from ...core.clients.mongodb_client import get_mongodb_client
from ...model.mongo.poi import POI, POISearchRequest, CategoryEnum, PriceLevelEnum
from ...utils.poi_dedupe import (
    generate_dedupe_key,
    normalize_poi_name,
    are_pois_duplicate
)
from .interfaces import POIRepositoryInterface

logger = logging.getLogger(__name__)


class POIRepository(POIRepositoryInterface):
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
            logger.info(f"[INFO] POI collection ready: {collection_name}")
        else:
            logger.error("[ERROR] Failed to get database for POI repository")
    
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
                logger.warning(f"[WARNING] Fuzzy duplicate found: {fuzzy_duplicate['poi_id']}")
                raise ValueError(
                    f"Similar POI already exists: {fuzzy_duplicate['poi_id']} "
                    f"(name: {fuzzy_duplicate['name']}, distance: <150m)"
                )
            
            # Insert into MongoDB
            result = self.collection.insert_one(poi_dict)
            
            logger.info(f"[INFO] Created POI: {poi_dict['poi_id']}")
            created_poi = self.collection.find_one({"_id": result.inserted_id})
            return created_poi
        
        except DuplicateKeyError as e:
            logger.error(f"[ERROR] Duplicate POI: {poi.dedupe_key}")
            # Find existing POI with same dedupe_key
            existing = self.collection.find_one({"dedupe_key": poi.dedupe_key})
            if existing:
                raise ValueError(
                    f"Duplicate POI: {existing['poi_id']} "
                    f"(name: {existing['name']}, dedupe_key: {poi.dedupe_key})"
                )
            raise
        
        except Exception as e:
            logger.error(f"[ERROR] Failed to create POI: {e}")
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
            logger.warning(f"[WARNING] Fuzzy duplicate check failed: {e}")
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
            logger.error(f"[ERROR] Failed to get POI {poi_id}: {e}")
            return None
        
    def get_by_google_id(self, google_place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get POI by Google Place ID.
        
        Args:
            google_place_id: Google Place identifier
            
        Returns:
            POI document if found, None otherwise
            
        Example:
            poi = poi_repo.get_by_google_id("ChIJoRyG2RwZQjERWLj1Xw8e9HE")
            if poi:
                print(f"Found: {poi['name']}")
        """
        if self.collection is None:
            return None
        
        try:
            poi = self.collection.find_one({"google_data.google_place_id": google_place_id})
            return poi
        
        except Exception as e:
            logger.error(f"[ERROR] Failed to get POI by Google ID {google_place_id}: {e}")
            return None
    
    def get_by_dedupe_key(self, dedupe_key: str) -> Optional[Dict[str, Any]]:
        """
        Get POI by deduplication key.
        
        Args:
            dedupe_key: Unique deduplication key (normalized_name + geohash)
            
        Returns:
            POI document if found, None otherwise
            
        Example:
            poi = poi_repo.get_by_dedupe_key("mykhebeach_wecq6uk")
            if poi:
                print(f"Found existing POI: {poi['name']}")
        """
        if self.collection is None:
            return None
        
        try:
            poi = self.collection.find_one({"dedupe_key": dedupe_key})
            return poi
        
        except Exception as e:
            logger.error(f"[ERROR] Failed to get POI by dedupe_key {dedupe_key}: {e}")
            return None
    
    def get_by_ids(self, poi_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get multiple POIs by their IDs.
        
        Args:
            poi_ids: List of POI identifiers
            
        Returns:
            Dict mapping poi_id to POI document
            
        Example:
            pois = poi_repo.get_by_ids(["poi_abc", "poi_xyz"])
            for poi_id, poi in pois.items():
                print(f"{poi_id}: {poi['name']}")
        """
        if self.collection is None or not poi_ids:
            return {}
        
        try:
            cursor = self.collection.find({"poi_id": {"$in": poi_ids}})
            result = {}
            for poi in cursor:
                result[poi['poi_id']] = poi
            
            logger.debug(f"[DEBUG] Fetched {len(result)}/{len(poi_ids)} POIs by IDs")
            return result
        
        except Exception as e:
            logger.error(f"[ERROR] Failed to get POIs by IDs: {e}")
            return {}

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
                logger.info(f"[INFO] Updated POI: {poi_id}")
            else:
                logger.warning(f"[WARNING] POI not found: {poi_id}")
            
            return result
        
        except Exception as e:
            logger.error(f"[ERROR] Failed to update POI {poi_id}: {e}")
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
                logger.info(f"[INFO] Deleted POI: {poi_id}")
                return True
            else:
                logger.warning(f"[WARNING] POI not found: {poi_id}")
                return False
        
        except Exception as e:
            logger.error(f"[ERROR] Failed to delete POI {poi_id}: {e}")
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
            pipeline = []
            match_stage = {}
            
            # Geo-spatial search (highest priority)
            # Note: $geoNear must be first stage, cannot combine with $text
            if search_request.lat and search_request.lng and search_request.radius:
                lng = search_request.lng
                lat = search_request.lat
                radius_meters = search_request.radius * 1000
                
                # Build query for $geoNear (includes text search if present)
                geo_query = {}
                if search_request.q:
                    # Use regex for text search when using $geoNear
                    geo_query["$or"] = [
                        {"name": {"$regex": search_request.q, "$options": "i"}},
                        {"description.short": {"$regex": search_request.q, "$options": "i"}},
                        {"categories": {"$regex": search_request.q, "$options": "i"}}
                    ]
                
                pipeline.append({
                    "$geoNear": {
                        "near": {
                            "type": "Point",
                            "coordinates": [lng, lat]
                        },
                        "distanceField": "distance_m",
                        "maxDistance": radius_meters,
                        "spherical": True,
                        "query": geo_query if geo_query else {}
                    }
                })
                
                # Add distance_km field
                pipeline.append({
                    "$addFields": {
                        "distance_km": {"$divide": ["$distance_m", 1000]}
                    }
                })
            elif search_request.q:
                # Text search only when no geo search
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
            
            # Add text search score (ONLY if using $text, not regex)
            # textScore is only available when $text search is used
            has_text_search = search_request.q and not (search_request.lat and search_request.lng)
            if has_text_search:
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
            # IMPORTANT: Always add "poi_id" as tie-breaker to ensure deterministic ordering
            # Without this, POIs with same score/rating will have random order between queries
            sort_stage = {}
            if has_text_search:
                # Only sort by search_score if $text was used
                sort_stage["search_score"] = -1
                sort_stage["poi_id"] = 1  # Tie-breaker for deterministic order
            elif search_request.lat and search_request.lng:
                # Geo search: sort by distance
                sort_stage["distance_km"] = 1
                sort_stage["poi_id"] = 1  # Tie-breaker for deterministic order
            else:
                # Default: sort by popularity and rating
                sort_stage["metadata.popularity_score"] = -1
                sort_stage["ratings.average"] = -1
                sort_stage["poi_id"] = 1  # Tie-breaker for deterministic order
            
            pipeline.append({"$sort": sort_stage})
            
            # Pagination
            skip = (search_request.page - 1) * search_request.limit
            pipeline.append({"$skip": skip})
            pipeline.append({"$limit": search_request.limit})
            
            # Execute query
            results = list(self.collection.aggregate(pipeline))
            
            # Calculate total pages
            total_pages = (total + search_request.limit - 1) // search_request.limit
            
            logger.info(f"[INFO] Search completed: {len(results)} results (total: {total})")
            
            return {
                "results": results,
                "total": total,
                "page": search_request.page,
                "limit": search_request.limit,
                "total_pages": total_pages
            }
        
        except Exception as e:
            logger.error(f"[ERROR] Search failed: {e}")
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
            logger.error(f"[ERROR] Get by category failed: {e}")
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
            
            logger.info(f"[INFO] Found {len(results)} nearby POI")
            
            return results
        
        except Exception as e:
            logger.error(f"[ERROR] Get nearby failed: {e}")
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
            logger.error(f"[ERROR] Get popular failed: {e}")
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
            logger.error(f"[ERROR] Count failed: {e}")
            return 0
    
    def upsert(self, poi: POI) -> Dict[str, Any]:
        """
        Upsert POI with write-through cache logic.
        
        Strategy:
        1. Check if POI exists (by poi_id or dedupe_key)
        2. If exists and fresh (not stale) → return existing
        3. If exists and stale → update with new data
        4. If not exists → insert new POI
        
        Args:
            poi: POI model instance
            
        Returns:
            Upserted POI document with metadata about operation
            
        Example:
            poi = POI(name="Mỹ Khê Beach", location={...}, ...)
            result = poi_repo.upsert(poi)
            print(f"Operation: {result['_operation']}")  # 'inserted', 'updated', 'skipped'
        """
        if self.collection is None:
            raise RuntimeError("POI collection not available")
        
        try:
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
            
            # Check if POI exists
            existing = self.collection.find_one({
                "$or": [
                    {"poi_id": poi_dict['poi_id']},
                    {"dedupe_key": poi_dict['dedupe_key']}
                ]
            })
            
            if existing:
                # POI exists, check if stale
                if self._is_stale(existing):
                    # Update stale POI
                    poi_dict['metadata']['updated_at'] = datetime.utcnow()
                    
                    result = self.collection.find_one_and_update(
                        {"_id": existing['_id']},
                        {"$set": poi_dict},
                        return_document=True
                    )
                    
                    logger.info(f"[REFRESH] Updated stale POI: {poi_dict['poi_id']} (provider: {poi_dict.get('metadata', {}).get('provider', 'unknown')})")
                    
                    result['_operation'] = 'updated'
                    result['_reason'] = 'stale_data'
                    return result
                else:
                    # POI is fresh, skip update
                    logger.info(f"[INFO] POI fresh, skip update: {poi_dict['poi_id']}")
                    
                    existing['_operation'] = 'skipped'
                    existing['_reason'] = 'fresh_data'
                    return existing
            else:
                # POI doesn't exist, insert new
                poi_dict['metadata']['created_at'] = datetime.utcnow()
                poi_dict['metadata']['updated_at'] = datetime.utcnow()
                
                result = self.collection.insert_one(poi_dict)
                
                logger.info(f"➕ Inserted new POI: {poi_dict['poi_id']} (provider: {poi_dict.get('metadata', {}).get('provider', 'unknown')})")
                created_poi = self.collection.find_one({"_id": result.inserted_id})
                created_poi['_operation'] = 'inserted'
                created_poi['_reason'] = 'new_poi'
                return created_poi
        
        except Exception as e:
            logger.error(f"[ERROR] Upsert failed: {e}")
            raise
    
    def _is_stale(self, poi: Dict[str, Any]) -> bool:
        """
        Check if POI data is stale and needs refresh.
        
        TTL Strategy:
        - Popular POI (>1000 reviews): 30 days
        - Normal POI: 90 days
        - Static POI (monuments, nature): 365 days
        - Restaurants/cafes: 60 days
        - Events/festivals: 7 days
        
        Args:
            poi: POI document
            
        Returns:
            True if POI is stale, False otherwise
        """
        updated_at = poi.get('metadata', {}).get('updated_at')
        
        if not updated_at:
            # No update timestamp, consider stale
            return True
        
        # Calculate age
        age = datetime.utcnow() - updated_at
        
        # Determine TTL based on POI characteristics
        total_reviews = poi.get('ratings', {}).get('count', 0)
        categories = poi.get('categories', [])
        
        # Popular POI: Refresh monthly
        if total_reviews > 1000:
            ttl_days = 30
        # Static POI: Refresh yearly
        elif any(cat in ['monument', 'natural_feature', 'park', 'beach'] for cat in categories):
            ttl_days = 365
        # Restaurants/cafes: Refresh bi-monthly
        elif any(cat in ['restaurant', 'cafe', 'bar'] for cat in categories):
            ttl_days = 60
        # Events: Refresh weekly
        elif any(cat in ['event', 'festival'] for cat in categories):
            ttl_days = 7
        # Default: Refresh quarterly
        else:
            ttl_days = 90
        
        is_stale = age.days > ttl_days
        
        if is_stale:
            logger.debug(f"POI {poi.get('poi_id')} is stale: {age.days} days old (TTL: {ttl_days} days)")
        
        return is_stale
    
    def bulk_upsert(self, pois: List[POI]) -> Dict[str, Any]:
        """
        Bulk upsert multiple POIs with optimized write-through cache.
        
        Strategy:
        1. Group POIs by operation (insert, update, skip)
        2. Use bulk_write for efficient DB operations
        3. Return statistics about operations
        
        Args:
            pois: List of POI model instances
            
        Returns:
            {
                "total": total POIs processed,
                "inserted": count of new POIs,
                "updated": count of updated POIs,
                "skipped": count of skipped POIs,
                "errors": count of errors,
                "inserted_ids": list of inserted poi_ids,
                "updated_ids": list of updated poi_ids,
                "skipped_ids": list of skipped poi_ids,
                "error_details": list of error messages
            }
            
        Example:
            pois = [POI(...), POI(...), POI(...)]
            result = poi_repo.bulk_upsert(pois)
            print(f"Inserted: {result['inserted']}, Updated: {result['updated']}")
        """
        if self.collection is None:
            raise RuntimeError("POI collection not available")
        
        if not pois:
            return {
                "total": 0,
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
                "errors": 0,
                "inserted_ids": [],
                "updated_ids": [],
                "skipped_ids": [],
                "error_details": []
            }
        
        try:
            from pymongo import UpdateOne, InsertOne
            
            stats = {
                "total": len(pois),
                "inserted": 0,
                "updated": 0,
                "skipped": 0,
                "errors": 0,
                "inserted_ids": [],
                "updated_ids": [],
                "skipped_ids": [],
                "error_details": []
            }
            
            # Prepare bulk operations
            bulk_operations = []
            
            for poi in pois:
                try:
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
                    
                    # Check if POI exists
                    existing = self.collection.find_one({
                        "$or": [
                            {"poi_id": poi_dict['poi_id']},
                            {"dedupe_key": poi_dict['dedupe_key']}
                        ]
                    })
                    
                    if existing:
                        # Check if stale
                        if self._is_stale(existing):
                            # Update operation
                            poi_dict['metadata']['updated_at'] = datetime.utcnow()
                            
                            bulk_operations.append(
                                UpdateOne(
                                    {"_id": existing['_id']},
                                    {"$set": poi_dict}
                                )
                            )
                            
                            stats['updated'] += 1
                            stats['updated_ids'].append(poi_dict['poi_id'])
                        else:
                            # Skip fresh POI
                            stats['skipped'] += 1
                            stats['skipped_ids'].append(poi_dict['poi_id'])
                    else:
                        # Insert operation
                        poi_dict['metadata']['created_at'] = datetime.utcnow()
                        poi_dict['metadata']['updated_at'] = datetime.utcnow()
                        
                        bulk_operations.append(
                            InsertOne(poi_dict)
                        )
                        
                        stats['inserted'] += 1
                        stats['inserted_ids'].append(poi_dict['poi_id'])
                
                except Exception as e:
                    stats['errors'] += 1
                    stats['error_details'].append({
                        "poi_id": poi_dict.get('poi_id', 'unknown'),
                        "error": str(e)
                    })
                    logger.error(f"[ERROR] Error processing POI: {e}")
            
            # Execute bulk operations
            if bulk_operations:
                bulk_result = self.collection.bulk_write(bulk_operations, ordered=False)
                
                logger.info(
                    f"[INFO] Bulk upsert completed: "
                    f"inserted={stats['inserted']}, "
                    f"updated={stats['updated']}, "
                    f"skipped={stats['skipped']}, "
                    f"errors={stats['errors']}"
                )
            else:
                logger.info("No operations to execute (all POIs skipped)")
            
            return stats
        
        except Exception as e:
            logger.error(f"[ERROR] Bulk upsert failed: {e}")
            raise
    
    def get_stale_pois(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get POIs that need refresh (stale data).
        
        Useful for background refresh jobs.
        
        Args:
            limit: Max POIs to return
            
        Returns:
            List of stale POI documents
            
        Example:
            stale_pois = poi_repo.get_stale_pois(limit=50)
            for poi in stale_pois:
                # Refresh from provider
                fresh_data = google_provider.get_details(poi['poi_id'])
                poi_repo.upsert(fresh_data)
        """
        if self.collection is None:
            return []
        
        try:
            all_pois = self.collection.find().limit(limit * 2)  # Get more to filter
            
            stale_pois = []
            for poi in all_pois:
                if self._is_stale(poi):
                    stale_pois.append(poi)
                    
                    if len(stale_pois) >= limit:
                        break
            
            logger.info(f"[INFO] Found {len(stale_pois)} stale POIs")
            
            return stale_pois
        
        except Exception as e:
            logger.error(f"[ERROR] Get stale POIs failed: {e}")
            return []
    
    def count_stale(self) -> int:
        """
        Count total stale POIs.
        
        Returns:
            Number of stale POIs
            
        Example:
            stale_count = poi_repo.count_stale()
            print(f"{stale_count} POIs need refresh")
        """
        if self.collection is None:
            return 0
        
        try:
            all_pois = self.collection.find()
            
            stale_count = 0
            for poi in all_pois:
                if self._is_stale(poi):
                    stale_count += 1
            
            return stale_count
        
        except Exception as e:
            logger.error(f"[ERROR] Count stale POIs failed: {e}")
            return 0
