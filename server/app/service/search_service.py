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

from ..repo.es.interfaces import ESPOIRepositoryInterface
from ..repo.mongo.interfaces import POIRepositoryInterface
from ..model.mongo.poi import POISearchRequest
from ..core.clients.elasticsearch_client import ElasticsearchClient

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
        google_provider: "GooglePlacesProvider" = None
    ):
        """
        Initialize search service with ES + MongoDB + Google fallback.
        
        Args:
            poi_repo: MongoDB POI repository (required, used as fallback + cache)
            es_repo: Elasticsearch POI repository (optional, primary search)
            google_provider: Google Places Provider (optional, external API fallback)
        """
        self.es_enabled = es_repo is not None and ElasticsearchClient.is_healthy()
        self.es_repo = es_repo if self.es_enabled else None
        self.mongo_repo = poi_repo  # Always available as fallback + cache
        self.google_provider = google_provider  # External API fallback
        
        if self.es_enabled:
            logger.info("[SearchService] Initialized with Elasticsearch + MongoDB")
        else:
            logger.warning("[SearchService] Initialized WITHOUT Elasticsearch (using MongoDB fallback)")
        
        if self.google_provider:
            logger.info("[SearchService] Google Places API fallback enabled")
        else:
            logger.warning("[SearchService] Google Places API fallback disabled")
    
    def search(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = 10.0,
        types: Optional[List[str]] = None,
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
            types: POI types filter (e.g., ["restaurant", "cafe"])
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
        logger.info(f"[SEARCH] query='{query}', lat={latitude}, lng={longitude}, radius={radius_km}km, types={types}")
        
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
                    types=types,
                    min_rating=min_rating,
                    price_levels=price_levels,
                    sort_by=sort_by,
                    limit=limit,
                    offset=offset
                )
                
                results = es_result.get('results', [])
                total = es_result.get('total', 0)
                source = "elasticsearch"
                logger.info(f"[SEARCH] ES: {len(results)} results in {es_result.get('took_ms', 0)}ms")
                
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
                types=types,
                min_rating=min_rating,
                price_levels=price_levels,
                limit=limit,
                offset=offset
            )
            results = mongo_result.get('results', [])
            total = mongo_result.get('total', 0)
            source = "mongodb"
            logger.info(f"[SEARCH] MongoDB fallback: {len(results)} results")
        
        # Step 3: If results < limit AND location provided, call Google Places API
        if len(results) < limit and latitude is not None and longitude is not None:
            if self.google_provider:
                try:
                    google_results = self._search_google(
                        latitude=latitude,
                        longitude=longitude,
                        radius_km=radius_km or 10.0,
                        types=types,
                        query=query if query else None,
                        max_results=limit - len(results)  # Only fetch what we need
                    )
                    
                    if google_results:
                        # Deduplicate: Only add POIs not already in results
                        existing_ids = {r.get('poi_id') or r.get('place_id') for r in results}
                        new_pois = [p for p in google_results if p.get('poi_id') not in existing_ids]
                        
                        # Cache new POIs to MongoDB + ES
                        cached_count = self._cache_pois(new_pois)
                        
                        # Add to results
                        results.extend(new_pois)
                        total += len(new_pois)
                        source = "hybrid" if source != "google_api" else "google_api"
                        
                        logger.info(f"[SEARCH] Google API: {len(new_pois)} new POIs, cached: {cached_count}")
                
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
            
            # Add distance to each POI
            for poi in pois:
                if poi and poi.get('location'):
                    coords = poi['location'].get('coordinates', [])
                    if len(coords) >= 2:
                        poi_lng, poi_lat = coords[0], coords[1]
                        poi['_distance_km'] = self._calculate_distance(
                            latitude, longitude, poi_lat, poi_lng
                        )
            
            logger.info(f"[GOOGLE] Nearby search: {len(pois)} POIs found")
            return pois
            
        except Exception as e:
            logger.error(f"[GOOGLE] Nearby search failed: {e}")
            return []
    
    def _cache_pois(self, pois: List[Dict[str, Any]]) -> int:
        """
        Cache POIs to both MongoDB and Elasticsearch.
        
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
                # Cache to MongoDB (primary storage)
                mongo_success = self._cache_poi_to_mongodb(poi)
                
                # Cache to Elasticsearch (for fast search)
                es_success = self._cache_poi_to_es(poi)
                
                if mongo_success or es_success:
                    cached_count += 1
                    
            except Exception as e:
                logger.error(f"[CACHE] Failed to cache POI {poi.get('poi_id')}: {e}")
        
        logger.info(f"[CACHE] Cached {cached_count}/{len(pois)} POIs to MongoDB + ES")
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
    
    # ============================================
    # NOTE: Old multi-index autocomplete methods REMOVED
    # Use AutocompleteService (autocomplete_service.py) instead
    # Hybrid architecture: ES autocomplete_cache + MongoDB + Google Places
    # Migration date: 2025-01
    # ============================================
    
    def get_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        types: Optional[List[str]] = None,
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
            types: POI types filter
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
            ...     types=["restaurant", "cafe"]
            ... )
        """
        logger.info(f"[LOCATION] Get nearby: lat={latitude}, lng={longitude}, radius={radius_km}km")
        
        # Use search with empty query (geo-only)
        results = self.search(
            query="",
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            types=types,
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
    
    def get_by_type(
        self,
        poi_type: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = None,
        min_rating: Optional[float] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get POIs by type (category).
        
        Use case: Browse by category (beaches, restaurants, museums, etc.)
        
        Args:
            poi_type: POI type/category (e.g., "beach", "restaurant")
            latitude: Optional center point
            longitude: Optional center point
            radius_km: Optional search radius
            min_rating: Optional minimum rating
            limit: Max results (default: 20)
        
        Returns:
            {
                "results": [POI dicts],
                "total": int,
                "type": str,
                "source": str
            }
        
        Example:
            >>> beaches = service.get_by_type(
            ...     poi_type="beach",
            ...     latitude=16.0544,
            ...     longitude=108.2428,
            ...     radius_km=20,
            ...     min_rating=4.0
            ... )
        """
        logger.info(f"[SEARCH] Get by type: type='{poi_type}', lat={latitude}, lng={longitude}")
        
        results = self.search(
            query=poi_type,  # Use type as query
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            types=[poi_type],  # Filter by type
            min_rating=min_rating,
            sort_by="rating" if not latitude else "distance",
            limit=limit
        )
        
        return {
            "results": results.get('results', []),
            "total": results.get('total', 0),
            "type": poi_type,
            "source": results.get('source', 'unknown')
        }
    
    def get_popular(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = None,
        types: Optional[List[str]] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get popular POIs (by rating + review count).
        
        Use case: "Top rated" or "Most popular" listings
        
        Args:
            latitude: Optional center point
            longitude: Optional center point
            radius_km: Optional search radius
            types: Optional type filters
            limit: Max results (default: 20)
        
        Returns:
            {
                "results": [POI dicts sorted by popularity],
                "total": int,
                "source": str
            }
        
        Example:
            >>> popular = service.get_popular(
            ...     latitude=16.0544,
            ...     longitude=108.2428,
            ...     radius_km=10,
            ...     limit=10
            ... )
        """
        logger.info(f"[RATING] Get popular: lat={latitude}, lng={longitude}, radius={radius_km}km")
        
        results = self.search(
            query="",
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            types=types,
            min_rating=4.0,  # Filter for quality
            sort_by="popularity",
            limit=limit
        )
        
        return {
            "results": results.get('results', []),
            "total": results.get('total', 0),
            "source": results.get('source', 'unknown')
        }
    
    # ========== PRIVATE HELPER METHODS ==========
    
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
