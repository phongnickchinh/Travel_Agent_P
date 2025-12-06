"""
Search Service - Elasticsearch Search Wrapper
==============================================

Purpose:
- High-level API for Elasticsearch POI search
- Autocomplete with edge n-gram
- Geo-distance search
- Full-text search with filters
- Graceful fallback to MongoDB

Author: Travel Agent P Team
Date: November 27, 2025
"""

import logging
from typing import List, Dict, Optional, Any

from ..repo.es.interfaces import ESPOIRepositoryInterface
from ..repo.mongo.interfaces import POIRepositoryInterface
from ..model.mongo.poi import POISearchRequest
from ..core.elasticsearch_client import ElasticsearchClient

logger = logging.getLogger(__name__)


class SearchService:
    """
    Search Service - Elasticsearch Wrapper with MongoDB Fallback
    
    Features:
    - Autocomplete search (edge n-gram) - 5-15ms latency
    - Geo-distance search (within radius) - 20-50ms latency
    - Full-text search with fuzzy matching
    - Multi-filter support (type, rating, price)
    - Sorting (relevance, distance, rating, popularity)
    - Graceful degradation (ES down → MongoDB)
    
    Architecture:
        User Query
            ↓
        Elasticsearch (FAST, 10-50ms)
            ↓ (if ES unavailable)
        MongoDB Fallback (SLOWER, 50-200ms)
    
    Example:
        service = SearchService()
        
        # Autocomplete
        suggestions = service.autocomplete("rest")
        
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
        es_repo: ESPOIRepositoryInterface = None
    ):
        """
        Initialize search service with ES + MongoDB fallback.
        
        Args:
            poi_repo: MongoDB POI repository (required, used as fallback)
            es_repo: Elasticsearch repository (optional)
        """
        self.es_enabled = es_repo is not None and ElasticsearchClient.is_healthy()
        self.es_repo = es_repo if self.es_enabled else None
        self.mongo_repo = poi_repo  # Always available as fallback
        
        if self.es_enabled:
            logger.info("[INFO] SearchService initialized with Elasticsearch")
        else:
            logger.warning("[WARNING] SearchService initialized WITHOUT Elasticsearch (using MongoDB fallback)")
    
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
        Search POIs with full-text + geo + filters.
        
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
                "source": "elasticsearch" | "mongodb",
                "page": int,
                "limit": int
            }
        
        Example:
            >>> results = service.search(
            ...     query="beach",
            ...     latitude=16.0544,
            ...     longitude=108.2428,
            ...     radius_km=5,
            ...     min_rating=4.0,
            ...     types=["beach", "nature"]
            ... )
            >>> for poi in results['results']:
            ...     print(f"{poi['name']} - {poi['_distance_km']:.2f}km")
        """
        logger.info(f"[SEARCH] Search: query='{query}', lat={latitude}, lng={longitude}, radius={radius_km}km")
        
        # Try Elasticsearch first
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
                
                logger.info(f"[INFO] Elasticsearch: {es_result['total']} results in {es_result['took_ms']}ms")
                return {
                    **es_result,
                    "source": "elasticsearch",
                    "page": (offset // limit) + 1,
                    "limit": limit
                }
            
            except Exception as e:
                logger.error(f"[ERROR] Elasticsearch search failed: {e}, falling back to MongoDB")
        
        # Fallback to MongoDB
        return self._search_mongodb(
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
    
    def autocomplete(self, prefix: str, limit: int = 10) -> List[str]:
        """
        Autocomplete POI names (edge n-gram).
        
        Use case: Search box autocomplete
        
        Args:
            prefix: Search prefix (e.g., "rest", "ca")
            limit: Max suggestions (default: 10)
        
        Returns:
            List of POI name suggestions
        
        Example:
            >>> suggestions = service.autocomplete("rest")
            >>> print(suggestions)
            ['Restaurant ABC', 'Restoran XYZ', 'Rest & Relax Cafe']
        """
        logger.info(f"[SEARCH] Autocomplete: prefix='{prefix}', limit={limit}")
        
        # Try Elasticsearch first (edge n-gram analyzer)
        if self.es_enabled and self.es_repo:
            try:
                suggestions = self.es_repo.autocomplete(prefix, size=limit)
                logger.info(f"[INFO] Elasticsearch autocomplete: {len(suggestions)} suggestions")
                return suggestions
            
            except Exception as e:
                logger.error(f"[ERROR] Elasticsearch autocomplete failed: {e}, falling back to MongoDB")
        
        # Fallback to MongoDB text search
        return self._autocomplete_mongodb(prefix, limit)
    
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
    
    def _autocomplete_mongodb(self, prefix: str, limit: int) -> List[str]:
        """MongoDB fallback autocomplete (text search)."""
        try:
            search_req = POISearchRequest(
                q=prefix,
                page=1,
                limit=limit
            )
            
            result = self.mongo_repo.search(search_req)
            suggestions = [poi.get('name', '') for poi in result.get('results', [])]
            
            logger.info(f"[INFO] MongoDB autocomplete: {len(suggestions)} suggestions")
            return suggestions
        
        except Exception as e:
            logger.error(f"[ERROR] MongoDB autocomplete failed: {e}")
            return []
