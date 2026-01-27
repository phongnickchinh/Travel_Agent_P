"""
Search Service - Hybrid Search with ES + MongoDB + Google API
=============================================================

Purpose:
- High-level API for POI search
- ES-First strategy: Query Elasticsearch first (5-15ms)
- MongoDB Fallback: If ES is down, use MongoDB (50ms)
- Google API Fallback: If local cache insufficient, call Google Nearby Search
- Auto-cache: Cache Google results to both MongoDB and ES

Architecture:
    User Query
           ↓
    ES Cache (5-15ms) ──→ Enough results? ──→ YES ──→ Return
           │                    │
           │                   NO
           ▼                    ↓
    MongoDB Fallback      Google Nearby API
      (if ES down)              │
           │                    │
           └────────────────────┘
                    │
                    ▼
            Cache Results (MongoDB + ES)
                    │
                    ▼
            Return to Frontend

Author: Travel Agent P Team
Date: November 27, 2025
Updated: January 2025 - Added hybrid architecture with Google API fallback
"""

import logging
import time
from typing import List, Dict, Optional, Any, TYPE_CHECKING

from ..repo.es.interfaces import ESPOIRepositoryInterface, ESPlanRepositoryInterface
from ..repo.mongo.interfaces import POIRepositoryInterface, PlanRepositoryInterface
from ..repo.mongo.plan_repository import PlanRepositoryInterface
from ..model.mongo.poi import POISearchRequest
from ..core.clients.elasticsearch_client import ElasticsearchClient
from ..providers.type_mapping import (
    map_user_interests_to_google_types,
    map_user_interests_to_categories
)

if TYPE_CHECKING:
    from ..providers.places.google_places_provider import GooglePlacesProvider

logger = logging.getLogger(__name__)


class SearchService:
    """
    Hybrid Search Service - ES + MongoDB + Google API Fallback
    
    Features:
    - Geo-distance search (within radius) - 20-50ms latency
    - Full-text search with fuzzy matching
    - Multi-filter support (type, rating, price)
    - Sorting (relevance, distance, rating, popularity)
    - Graceful degradation (ES down → MongoDB)
    - Google API fallback when local cache insufficient
    - Auto-cache: Save Google results to MongoDB + ES
    
    Architecture:
        User Query
            ↓
        Elasticsearch (FAST, 10-50ms)
            ↓ (if ES unavailable)
        MongoDB Fallback (SLOWER, 50-200ms)
            ↓ (if results < limit)
        Google Places API Nearby Search
            ↓
        Cache to MongoDB + ES
            ↓
        Return to Frontend
    
    Example:
        service = SearchService(poi_repo, es_repo, google_provider)
        
        # Geo search
        results = service.search(
            query="cafe",
            latitude=16.0544,
            longitude=108.2428,
            radius_km=5,
            min_rating=4.0
        )
        
        # Get nearby
        nearby = service.get_nearby(
            latitude=16.0544,
            longitude=108.2428,
            radius_km=2
        )
    """
    
    def __init__(
        self, 
        poi_repo: POIRepositoryInterface,
        es_repo: ESPOIRepositoryInterface = None,
        es_plan_repo: ESPlanRepositoryInterface = None,
        plan_repo: PlanRepositoryInterface = None,
        google_provider: "GooglePlacesProvider" = None
    ):
        self.es_enabled = es_repo is not None and ElasticsearchClient.is_healthy()
        self.es_repo = es_repo if self.es_enabled else None
        self.es_plan_repo = es_plan_repo if self.es_enabled else None
        self.mongo_repo = poi_repo
        self.plan_repo = plan_repo
        self.google_provider = google_provider
        
        if self.es_enabled:
            logger.info("[SearchService] Initialized with Elasticsearch + MongoDB")
        else:
            logger.warning("[SearchService] Initialized WITHOUT Elasticsearch (using MongoDB fallback)")
        
        if self.google_provider:
            logger.info("[SearchService] Google Places API fallback enabled")
        else:
            logger.warning("[SearchService] Google Places API fallback disabled")
    
    def search_poi(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = 10.0,
        types: Optional[List[str]] = None,
        interests: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        price_levels: Optional[List[str]] = None,
        sort_by: str = "relevance",
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Hybrid search: ES → MongoDB → Google API fallback.
        
        Args:
            query: Search query string (e.g., "vietnamese restaurant")
            latitude: Center point latitude (for geo-distance)
            longitude: Center point longitude (for geo-distance)
            radius_km: Search radius in km (default: 10)
            types: POI types filter - Google Place Types (direct pass-through to Google API)
            interests: User interest IDs (e.g., ['beach', 'culture']) - converted to appropriate types per backend
            min_rating: Minimum average rating (0-5)
            price_levels: Price levels (e.g., ["MODERATE", "INEXPENSIVE"])
            sort_by: Sort order - "relevance", "distance", "rating", "popularity"
            limit: Max results (default: 20)
            offset: Pagination offset (default: 0)
        
        Returns:
            {
                "results": [POI dicts with _score and _distance_km],
                "total": int,
                "took_ms": int,
                "source": "elasticsearch" | "mongodb" | "google_api" | "hybrid",
                "page": int,
                "limit": int
            }
        """
        start_time = time.time()
        logger.debug("[SEARCH] query='%s', lat=%s, lng=%s, radius=%skm, types=%s, interests=%s", query, latitude, longitude, radius_km, types, interests)
        
        # Convert interests to appropriate types for each backend
        # ES/MongoDB use CategoryEnum values, Google API uses Google Place Types
        es_mongo_types = types  # Pass-through if types provided directly
        google_types = types    # Pass-through if types provided directly
        
        if interests and not types:
            # Convert for ES/MongoDB (CategoryEnum values as strings)
            categories = map_user_interests_to_categories(interests)
            if categories:
                es_mongo_types = [cat.value for cat in categories]  # CategoryEnum.BEACH -> "BEACH"
                logger.debug("[SEARCH] Mapped interests %s -> ES/Mongo categories %s", interests, es_mongo_types)
            
            # Convert for Google API (Google Place Types)
            google_types = map_user_interests_to_google_types(interests)
            if google_types:
                logger.debug("[SEARCH] Mapped interests %s -> Google types %s", interests, google_types)
        
        results = []
        source = "unknown"
        total = 0
        
        # Step 1: Try Elasticsearch first (ES and MongoDB share the same data source)
        if self.es_enabled and self.es_repo:
            try:
                location = None
                if latitude is not None and longitude is not None:
                    location = {"latitude": latitude, "longitude": longitude}
                
                es_result = self.es_repo.search(
                    query=query,
                    location=location,
                    radius_km=radius_km,
                    types=es_mongo_types,  # Use CategoryEnum values for ES
                    min_rating=min_rating,
                    price_levels=price_levels,
                    sort_by=sort_by,
                    limit=limit,
                    offset=offset
                )
                
                results = es_result.get('results', [])
                total = es_result.get('total', 0)
                source = "elasticsearch"
                logger.debug("[SEARCH] ES: %d results in %dms", len(results), es_result.get('took_ms', 0))
                
            except Exception as e:
                logger.error(f"[SEARCH] ES failed: {e}, trying MongoDB fallback")
                source = "error"
        
        # Step 2: If ES failed or unavailable, fallback to MongoDB (shared data source)
        if source == "error" or source == "unknown":
            mongo_result = self._search_mongodb(
                query=query,
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                types=es_mongo_types,  # Use CategoryEnum values for MongoDB
                min_rating=min_rating,
                price_levels=price_levels,
                limit=limit,
                offset=offset
            )
            results = mongo_result.get('results', [])
            total = mongo_result.get('total', 0)
            source = "mongodb"
            logger.debug("[SEARCH] MongoDB fallback: %d results", len(results))
        
        # Step 3: If results < limit AND location provided, call Google Places API
        if len(results) < limit and latitude is not None and longitude is not None:
            if self.google_provider:
                try:
                    google_results = self._search_google(
                        latitude=latitude,
                        longitude=longitude,
                        radius_km=radius_km or 10.0,
                        types=google_types,  # Use Google Place Types for Google API
                        query=query if query else None,
                        max_results=limit - len(results)  # Only fetch what we need
                    )
                    
                    if google_results:
                        # Deduplicate: Only add POIs not already in results
                        existing_ids = {r.get('poi_id') or r.get('place_id') for r in results}
                        new_pois = [p for p in google_results if p.get('poi_id') not in existing_ids]
                        
                        # Cache new POIs to MongoDB + ES
                        cached_count = self._cache_pois(new_pois)
                        
                        # Add to results (strip _original_poi before adding)
                        for poi in new_pois:
                            poi.pop('_original_poi', None)
                        results.extend(new_pois)
                        total += len(new_pois)
                        source = "hybrid" if source != "google_api" else "google_api"
                        
                        logger.debug("[SEARCH] Google API: %d new POIs, cached: %d", len(new_pois), cached_count)
                
                except Exception as e:
                    logger.error(f"[SEARCH] Google API fallback failed: {e}")
            else:
                logger.debug("[SEARCH] Google API fallback disabled (no provider)")
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return {
            "results": results[:limit],  # Ensure we don't exceed limit
            "total": total,
            "took_ms": elapsed_ms,
            "source": source,
            "page": (offset // limit) + 1,
            "limit": limit
        }
    
    def _search_google(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        types: Optional[List[str]] = None,
        query: Optional[str] = None,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search Google Places Nearby API.
        
        Note: GooglePlacesProvider.nearby_search() already transforms the response
        to our POI schema, so we just need to add distance calculation.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Search radius in km
            types: POI types filter
            query: Optional text query
            max_results: Maximum results to fetch
        
        Returns:
            List of POI dicts already in our schema format
        """
        if not self.google_provider:
            return []
        
        try:
            # Convert types to Google Places format
            google_types = self._map_types_to_google(types) if types else None
            
            # Call Google Nearby Search - returns already-transformed POIs
            location = {"latitude": latitude, "longitude": longitude}
            radius_meters = int(radius_km * 1000)
            
            pois = self.google_provider.nearby_search(
                location=location,
                radius=radius_meters,
                types=google_types,
                max_results=max_results
            )
            
            # Transform POIs to frontend-friendly format and add distance
            transformed_pois = []
            for poi in pois:
                if poi:
                    # Transform to frontend format (flat latitude/longitude)
                    frontend_poi = self._transform_poi_for_frontend(poi)
                    
                    # Calculate distance
                    poi_lat = frontend_poi.get('latitude', 0)
                    poi_lng = frontend_poi.get('longitude', 0)
                    if poi_lat and poi_lng:
                        frontend_poi['_distance_km'] = self._calculate_distance(
                            latitude, longitude, poi_lat, poi_lng
                        )
                    
                    # Also keep original POI for caching (MongoDB/ES need provider format)
                    frontend_poi['_original_poi'] = poi
                    transformed_pois.append(frontend_poi)
            
            logger.debug("[GOOGLE] Nearby search: %d POIs found", len(transformed_pois))
            return transformed_pois
            
        except Exception as e:
            logger.error(f"[GOOGLE] Nearby search failed: {e}")
            return []
    
    def _cache_pois(self, pois: List[Dict[str, Any]]) -> int:
        """
        Cache POIs to both MongoDB and Elasticsearch.
        
        POIs may be in frontend format (with _original_poi) or provider format.
        Uses _original_poi for caching if available.
        
        Args:
            pois: List of POI dicts to cache
        
        Returns:
            Number of POIs successfully cached
        """
        if not pois:
            return 0
        
        cached_count = 0
        
        for poi in pois:
            try:
                # Use original provider format if available (for proper MongoDB/ES schema)
                original_poi = poi.get('_original_poi', poi)
                
                # Cache to MongoDB (primary storage)
                mongo_success = self._cache_poi_to_mongodb(original_poi)
                
                # Cache to Elasticsearch (for fast search)
                es_success = self._cache_poi_to_es(original_poi)
                
                if mongo_success or es_success:
                    cached_count += 1
                    
            except Exception as e:
                logger.error(f"[CACHE] Failed to cache POI {poi.get('poi_id')}: {e}")
        
        logger.debug("[CACHE] Cached %d/%d POIs to MongoDB + ES", cached_count, len(pois))
        return cached_count
    
    def _cache_poi_to_mongodb(self, poi: Dict[str, Any]) -> bool:
        """
        Cache a single POI to MongoDB with deduplication.
        
        The POI dict is expected to be in the format returned by 
        GooglePlacesProvider.transform_to_poi(), which already matches 
        our MongoDB POI schema.
        
        Args:
            poi: POI dict from provider (already transformed to our schema)
        
        Returns:
            True if cached successfully, False otherwise
        """
        try:
            # The provider already generates poi_id and dedupe_key
            dedupe_key = poi.get('dedupe_key')
            poi_id = poi.get('poi_id')
            
            if not dedupe_key:
                from ..utils.poi_dedupe import generate_dedupe_key
                coords = poi.get('location', {}).get('coordinates', [0, 0])
                lng, lat = coords[0], coords[1]
                dedupe_key = generate_dedupe_key(
                    name=poi.get('name', ''),
                    lat=lat,
                    lng=lng
                )
                poi['dedupe_key'] = dedupe_key
                poi['poi_id'] = poi_id or f"poi_{dedupe_key}"
            
            # Check if already exists
            existing = self.mongo_repo.get_by_dedupe_key(dedupe_key)
            if existing:
                logger.debug(f"[CACHE] POI already exists in MongoDB: {dedupe_key}")
                return False
            
            # Insert directly to MongoDB (dict already matches our schema)
            # Use the repository's collection directly since the dict is pre-formatted
            collection = self.mongo_repo.collection
            if collection is None:
                logger.error("[CACHE] MongoDB collection not available")
                return False
            
            # Ensure required fields are present
            if 'metadata' not in poi:
                from datetime import datetime
                poi['metadata'] = {
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            
            collection.insert_one(poi)
            logger.debug(f"[CACHE] POI cached to MongoDB: {poi_id}")
            return True
            
        except Exception as e:
            logger.error(f"[CACHE] MongoDB cache failed for {poi.get('poi_id')}: {e}")
            return False
    
    def _cache_poi_to_es(self, poi: Dict[str, Any]) -> bool:
        """
        Cache a single POI to Elasticsearch.
        
        Args:
            poi: POI dict to cache
        
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.es_enabled or not self.es_repo:
            return False
        
        try:
            self.es_repo.index_poi(poi)
            return True
        except Exception as e:
            logger.error(f"[CACHE] ES cache failed for {poi.get('poi_id')}: {e}")
            return False
    
    def _map_types_to_google(self, types: List[str]) -> List[str]:
        """
        Map our POI types to Google Places types.
        
        Args:
            types: Our POI types
        
        Returns:
            List of Google Places types
        """
        type_mapping = {
            "restaurant": "restaurant",
            "cafe": "cafe",
            "bar": "bar",
            "hotel": "lodging",
            "museum": "museum",
            "park": "park",
            "beach": "natural_feature",
            "temple": "hindu_temple",
            "pagoda": "place_of_worship",
            "market": "shopping_mall",
            "shopping": "shopping_mall",
            "attraction": "tourist_attraction",
            "landmark": "landmark",
            "nature": "natural_feature",
            "spa": "spa",
            "gym": "gym"
        }
        
        google_types = []
        for t in types:
            mapped = type_mapping.get(t.lower(), t)
            if mapped not in google_types:
                google_types.append(mapped)
        
        return google_types
    
    def _transform_poi_for_frontend(self, poi: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform provider POI (GeoJSON format) to frontend-friendly format.
        
        The provider returns:
        - location: {type: "Point", coordinates: [lng, lat]}
        - ratings: {average, count}
        - address: {full_address, ...}
        
        Frontend expects:
        - location: {latitude, longitude}
        - latitude, longitude (flat)
        - rating, total_reviews (flat)
        - address (string)
        
        Args:
            poi: POI dict from GooglePlacesProvider.transform_to_poi()
        
        Returns:
            Frontend-friendly POI dict
        """
        # Extract location from GeoJSON format
        location = poi.get('location', {})
        lat = 0.0
        lng = 0.0
        
        if isinstance(location, dict):
            if 'coordinates' in location:
                coords = location.get('coordinates', [0, 0])
                if len(coords) >= 2:
                    lng = coords[0]
                    lat = coords[1]
            elif 'latitude' in location:
                lat = location.get('latitude', 0.0)
                lng = location.get('longitude', 0.0)
        
        # Extract ratings
        ratings = poi.get('ratings', {})
        rating = 0.0
        total_reviews = 0
        if isinstance(ratings, dict):
            rating = ratings.get('average', 0.0)
            total_reviews = ratings.get('count', 0)
        
        # Extract address
        address = poi.get('address', {})
        address_str = ''
        if isinstance(address, dict):
            address_str = address.get('full_address', address.get('short_address', ''))
        elif isinstance(address, str):
            address_str = address
        
        # Extract description
        description = poi.get('description', {})
        description_str = ''
        if isinstance(description, dict):
            description_str = description.get('short', description.get('long', ''))
        elif isinstance(description, str):
            description_str = description
        
        # Extract pricing
        pricing = poi.get('pricing', {})
        price_level = ''
        if isinstance(pricing, dict):
            price_level = pricing.get('level', '')
        
        # Extract contact
        contact = poi.get('contact', {})
        google_maps_uri = ''
        if isinstance(contact, dict):
            google_maps_uri = contact.get('google_maps_uri', '')
        
        # Extract photos
        images = poi.get('images', [])
        photos = []
        photo_reference = None
        if isinstance(images, list):
            for img in images[:5]:
                if isinstance(img, dict):
                    ref = img.get('photo_reference', img.get('url', ''))
                    if ref:
                        photos.append(ref)
                        if not photo_reference:
                            photo_reference = ref
        
        # Extract types
        types = poi.get('categories', poi.get('types', []))
        primary_type = ''
        google_data = poi.get('google_data', {})
        if google_data:
            primary_type = google_data.get('primary_type', '')
        if not primary_type and types:
            primary_type = types[0] if isinstance(types, list) and types else ''
        
        return {
            'poi_id': poi.get('poi_id'),
            'dedupe_key': poi.get('dedupe_key'),
            'name': poi.get('name', ''),
            'name_unaccented': poi.get('name_unaccented', ''),
            
            # Flat location for frontend
            'latitude': lat,
            'longitude': lng,
            'location': {
                'latitude': lat,
                'longitude': lng
            },
            
            'address': address_str,
            
            'rating': rating,
            'total_reviews': total_reviews,
            
            'types': types,
            'primary_type': primary_type,
            'category': primary_type or (types[0] if types else ''),
            
            'price_level': price_level,
            
            'description': description_str,
            
            'photo_reference': photo_reference,
            'photos': photos,
            'photos_count': len(images) if isinstance(images, list) else 0,
            
            'google_maps_uri': google_maps_uri,
            
            'opening_hours': poi.get('opening_hours', {}),
            'amenities': poi.get('amenities', []),
            
            'provider': 'google_places'
        }
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate distance between two coordinates in kilometers.
        Uses Haversine formula.
        """
        import math
        
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return round(R * c, 2)

    def _search_mongodb(
        self,
        query: str,
        latitude: Optional[float],
        longitude: Optional[float],
        radius_km: Optional[float],
        types: Optional[List[str]],
        min_rating: Optional[float],
        price_levels: Optional[List[str]],
        limit: int,
        offset: int
    ) -> Dict[str, Any]:
        """MongoDB fallback search."""
        try:
            page = (offset // limit) + 1
            
            search_req = POISearchRequest(
                q=query,
                lat=latitude,
                lng=longitude,
                radius=radius_km,
                categories=types,
                min_rating=min_rating,
                price_level=price_levels[0] if price_levels else None,
                page=page,
                limit=limit
            )
            
            result = self.mongo_repo.search(search_req)
            
            logger.info(f"[INFO] MongoDB fallback: {result['total']} results")
            
            return {
                "results": result.get('results', []),
                "total": result.get('total', 0),
                "took_ms": 0,  # MongoDB doesn't provide timing
                "source": "mongodb",
                "page": page,
                "limit": limit
            }
        
        except Exception as e:
            logger.error(f"[ERROR] MongoDB search failed: {e}")
            return {
                "results": [],
                "total": 0,
                "took_ms": 0,
                "source": "error",
                "page": page,
                "limit": limit
            }


    def get_poi_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        types: Optional[List[str]] = None,
        interests: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get POIs near a location (no text query).
        
        Use case: "What's nearby?" feature
        
        Args:
            latitude: Center point latitude
            longitude: Center point longitude
            radius_km: Search radius in km (default: 5)
            types: POI types filter (Google Place Types, direct pass-through)
            interests: User interest IDs (e.g., 'beach', 'culture', 'food') - converted to Google types
            min_rating: Minimum rating
            limit: Max results (default: 20)
        
        Returns:
            {
                "results": [POI dicts with _distance_km],
                "total": int,
                "center": {"latitude": float, "longitude": float},
                "radius_km": float
            }
        
        Example:
            >>> nearby = service.get_nearby(
            ...     latitude=16.0544,
            ...     longitude=108.2428,
            ...     radius_km=2,
            ...     interests=["beach", "food"]  # Converted to Google types internally
            ... )
        """
        logger.info(f"[NEARBY] Get nearby: lat={latitude}, lng={longitude}, radius={radius_km}km, interests={interests}")
        
        # Use search with empty query (geo-only)
        # Pass interests directly - search() handles conversion for each backend
        results = self.search_poi(
            query="",
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            types=types,
            interests=interests,  # Pass interests directly, search() converts per backend
            min_rating=min_rating,
            sort_by="distance",
            limit=limit
        )
        
        return {
            "results": results.get('results', []),
            "total": results.get('total', 0),
            "center": {"latitude": latitude, "longitude": longitude},
            "radius_km": radius_km,
            "source": results.get('source', 'unknown')
        }

    def search_user_plan(
        self,
        query: str,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        if not user_id:
            return {"results": [], "total": 0, "source": "error"}
        
        start_time = time.time()
        
        if self.es_enabled and self.es_plan_repo:
            try:
                result = self.es_plan_repo.search(query=query, user_id=user_id, limit=limit, offset=offset)
                took_ms = int((time.time() - start_time) * 1000)
                return {
                    "results": result.get("results", []),
                    "total": result.get("total", 0),
                    "took_ms": took_ms,
                    "source": "elasticsearch"
                }
            except Exception as e:
                logger.warning(f"[SEARCH_PLAN] ES failed, fallback to MongoDB: {e}")
        
        if self.plan_repo:
            try:
                plans = self.plan_repo.search_by_user(
                    user_id=user_id,
                    query=query,
                    limit=limit,
                    offset=offset
                )
                took_ms = int((time.time() - start_time) * 1000)
                results = [{"plan_id": p.plan_id, "title": p.title, "destination": p.destination} for p in plans]
                return {
                    "results": results,
                    "total": len(results),
                    "took_ms": took_ms,
                    "source": "mongodb"
                }
            except Exception as e:
                logger.error(f"[SEARCH_PLAN] MongoDB search failed: {e}")
        
        return {"results": [], "total": 0, "source": "error"}