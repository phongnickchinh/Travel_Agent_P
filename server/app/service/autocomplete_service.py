"""
Autocomplete Service - Hybrid Autocomplete with ES Cache + Google Fallback
==========================================================================

Purpose:
- ES-First strategy: Query Elasticsearch cache first (5-15ms)
- MongoDB Fallback: If ES is down, use MongoDB (50ms)
- Google API Fallback: If local cache insufficient, call Google Autocomplete
- Click-to-Enrich: Fetch full details only when user clicks
- Auto-populate: Cache Google predictions for future searches

Architecture:
    User Types Query
           ↓
    ES Cache (5-15ms) ──→ Enough results? ──→ YES ──→ Return
           │                    │
           │                   NO
           ▼                    ↓
    MongoDB Fallback      Google Autocomplete API
      (if ES down)           (< $3/1000)
           │                    │
           └────────────────────┘
                    │
                    ▼
            Merge & Cache Results
                    │
                    ▼
            Return to Frontend

Author: Travel Agent P Team
Date: December 22, 2025
Updated: December 23, 2025 (Anti-abuse protection)
"""

import logging
import unicodedata
from typing import List, Dict, Optional, Any, TYPE_CHECKING
from datetime import datetime

from ..model.mongo.autocomplete_cache import AutocompleteItem, CacheStatus
from ..repo.es.interfaces import ESAutocompleteRepositoryInterface
from ..repo.mongo.interfaces import AutocompleteRepositoryInterface
from ..core.clients.elasticsearch_client import ElasticsearchClient
from ..core.clients.redis_client import get_redis
from config import Config

if TYPE_CHECKING:
    from ..providers.places.google_places_provider import GooglePlacesProvider

logger = logging.getLogger(__name__)


class AutocompleteService:
    """
    Hybrid Autocomplete Service with multi-layer caching.
    
    Layers:
    1. Elasticsearch Cache (primary, ~5-15ms)
    2. MongoDB (fallback when ES down, ~50ms)
    3. Google Autocomplete API (fallback when cache insufficient, ~200-300ms)
    
    Anti-Abuse Protection:
    - Negative Query Cache: Cache queries with 0 Google results (prevent repeated API calls)
    - Daily API Quota: Limit Google API calls per day (prevent bill shock)
    
    Features:
    - Cost-effective: Google Autocomplete is cheap (~$2.83/1000)
    - Auto-enriching: Cache grows from user searches
    - Click-to-resolve: Only fetch details on user click
    - Popularity tracking: Click count for relevance boost
    
    Example:
        service = AutocompleteService(es_repo, mongo_repo, google_provider)
        
        # Search with hybrid strategy
        results = service.autocomplete("Paris", limit=5)
        # Returns: {"suggestions": [...], "total": 5, "source": "es+google"}
        
        # User clicks a suggestion
        details = service.resolve("ChIJD7fiBh9u5kcRYJSMaMOCCwQ")
        # Fetches full details from Google, caches to MongoDB/ES
    """
    
    # Minimum ES results before calling Google API
    MIN_ES_RESULTS = 3
    
    # Default result limit
    DEFAULT_LIMIT = 5
    
    # Redis key prefixes for anti-abuse
    NEGATIVE_CACHE_PREFIX = "autocomplete:negative:"
    DAILY_QUOTA_KEY = "autocomplete:google_api:daily_count"
    
    def __init__(
        self,
        es_repo: ESAutocompleteRepositoryInterface = None,
        mongo_repo: AutocompleteRepositoryInterface = None,
        google_provider: 'GooglePlacesProvider' = None
    ):
        """
        Initialize Autocomplete Service.
        
        Args:
            es_repo: Elasticsearch autocomplete repository
            mongo_repo: MongoDB autocomplete repository
            google_provider: Google Places provider for API calls
        """
        self.es_repo = es_repo
        self.mongo_repo = mongo_repo
        self.google_provider = google_provider
        self._redis = get_redis()
        
        # Check ES health
        self.es_enabled = es_repo is not None and ElasticsearchClient.is_healthy()
        
        if self.es_enabled:
            logger.info("[INFO] AutocompleteService initialized with ES + MongoDB + Google")
        elif mongo_repo:
            logger.warning("[WARNING] AutocompleteService initialized WITHOUT ES (MongoDB + Google only)")
        else:
            logger.warning("[WARNING] AutocompleteService initialized with Google only")
    
    # ============================================
    # LAYER 2: Negative Query Cache (Anti-Abuse)
    # ============================================
    
    def _normalize_query_for_cache(self, query: str) -> str:
        """
        Normalize query for cache key.
        - Lowercase
        - Remove accents
        - Remove extra whitespace
        """
        if not query:
            return ""
        # Normalize to NFD, remove accents
        nfkd = unicodedata.normalize('NFD', query.lower())
        without_accents = ''.join(c for c in nfkd if not unicodedata.combining(c))
        # Replace đ/Đ explicitly (not handled by NFD)
        without_accents = without_accents.replace('đ', 'd').replace('Đ', 'D')
        # Normalize whitespace
        return ' '.join(without_accents.split())
    
    def _is_negative_cached(self, query: str) -> bool:
        """
        Check if query is in negative cache (previously returned 0 results from Google).
        
        Returns True if query should be skipped (known to have no results).
        """
        if not Config.NEGATIVE_CACHE_ENABLED or not self._redis:
            return False
        
        try:
            cache_key = self.NEGATIVE_CACHE_PREFIX + self._normalize_query_for_cache(query)
            return self._redis.exists(cache_key)
        except Exception as e:
            logger.warning(f"[NEGATIVE_CACHE] Check failed: {e}")
            return False
    
    def _add_to_negative_cache(self, query: str) -> None:
        """
        Add query to negative cache (Google returned 0 results).
        
        This prevents repeated Google API calls for the same useless query.
        TTL: Configurable (default 15 minutes)
        """
        if not Config.NEGATIVE_CACHE_ENABLED or not self._redis:
            return
        
        try:
            cache_key = self.NEGATIVE_CACHE_PREFIX + self._normalize_query_for_cache(query)
            self._redis.setex(cache_key, Config.NEGATIVE_CACHE_TTL, "1")
            logger.info(f"[NEGATIVE_CACHE] Cached negative result for: '{query}' (TTL: {Config.NEGATIVE_CACHE_TTL}s)")
        except Exception as e:
            logger.warning(f"[NEGATIVE_CACHE] Add failed: {e}")
    
    # ============================================
    # LAYER 3: Daily API Quota (Anti-Abuse)
    # ============================================
    
    def _check_daily_quota(self) -> tuple[bool, int, int]:
        """
        Check if daily Google API quota is exhausted.
        
        Returns:
            (is_allowed, current_count, max_quota)
        """
        if not self._redis:
            return True, 0, Config.GOOGLE_API_DAILY_QUOTA
        
        try:
            count = self._redis.get(self.DAILY_QUOTA_KEY)
            current_count = int(count) if count else 0
            max_quota = Config.GOOGLE_API_DAILY_QUOTA
            
            is_allowed = current_count < max_quota
            
            # Alert if approaching limit
            if current_count >= max_quota * Config.GOOGLE_API_QUOTA_ALERT_THRESHOLD:
                logger.warning(
                    f"[QUOTA_ALERT] Google API quota at {current_count}/{max_quota} "
                    f"({current_count/max_quota*100:.1f}%)"
                )
            
            return is_allowed, current_count, max_quota
        except Exception as e:
            logger.warning(f"[QUOTA] Check failed: {e}")
            return True, 0, Config.GOOGLE_API_DAILY_QUOTA
    
    def _increment_daily_quota(self) -> None:
        """
        Increment daily Google API call counter.
        Counter resets at midnight UTC.
        """
        if not self._redis:
            return
        
        try:
            pipe = self._redis.pipeline()
            pipe.incr(self.DAILY_QUOTA_KEY)
            # Set expiry to end of day (seconds until midnight UTC)
            now = datetime.utcnow()
            seconds_until_midnight = (24 - now.hour - 1) * 3600 + (60 - now.minute) * 60 + (60 - now.second)
            pipe.expire(self.DAILY_QUOTA_KEY, seconds_until_midnight)
            pipe.execute()
        except Exception as e:
            logger.warning(f"[QUOTA] Increment failed: {e}")
    
    def get_quota_stats(self) -> Dict[str, Any]:
        """Get current quota usage statistics."""
        is_allowed, current, maximum = self._check_daily_quota()
        return {
            "google_api_calls_today": current,
            "google_api_daily_limit": maximum,
            "quota_remaining": maximum - current,
            "quota_exhausted": not is_allowed,
            "quota_percentage": round(current / maximum * 100, 1) if maximum > 0 else 0
        }
    
    def autocomplete(
        self,
        query: str,
        limit: int = DEFAULT_LIMIT,
        types: Optional[List[str]] = None,
        location: Optional[Dict[str, float]] = None,
        session_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Hybrid autocomplete with ES cache + Google fallback.
        
        Strategy:
        1. Query ES cache first (fast, ~5-15ms)
        2. If >= MIN_ES_RESULTS with good scores → return immediately
        3. If < MIN_ES_RESULTS → call Google Autocomplete API
        4. Merge results, cache Google predictions
        5. Return combined results
        
        Args:
            query: Search query (e.g., "Paris", "Bãi biển")
            limit: Maximum results to return (default: 10)
            types: Filter by place types (e.g., ["locality", "restaurant"])
            location: User location for geo-boosting {"latitude": float, "longitude": float}
            session_token: Google session token for billing (optional)
        
        Returns:
            {
                "suggestions": [
                    {
                        "place_id": "ChIJ...",
                        "description": "Paris, France",
                        "main_text": "Paris",
                        "secondary_text": "France",
                        "types": ["locality", "political"],
                        "status": "cached" | "pending",
                        "source": "es" | "google" | "mongodb"
                    }
                ],
                "total": int,
                "sources": {"es": int, "google": int, "mongodb": int},
                "query_time_ms": float
            }
        """
        start_time = datetime.utcnow()
        
        if not query or len(query.strip()) < 1:
            return self._empty_response()
        
        query = query.strip()
        logger.info(f"[AUTOCOMPLETE] Query: '{query}', limit={limit}, types={types}")
        
        results = []
        sources = {"es": 0, "google": 0, "mongodb": 0}
        
        # ============================================
        # LAYER 1: Elasticsearch Cache (Primary)
        # ============================================
        if self.es_enabled and self.es_repo:
            try:
                es_results = self.es_repo.search(
                    query=query,
                    limit=limit,
                    location=location,
                    types=types
                )
                
                for item in es_results:
                    item["source"] = "es"
                    results.append(item)
                
                sources["es"] = len(es_results)
                logger.debug(f"[ES] Found {len(es_results)} cached results")
                
                # If enough good results from ES, return early
                if len(es_results) >= self.MIN_ES_RESULTS:
                    logger.info(f"[AUTOCOMPLETE] ES cache hit: {len(es_results)} results")
                    return self._build_response(results[:limit], sources, start_time)
                    
            except Exception as e:
                logger.warning(f"[ES] Search failed, falling back: {e}")
                self.es_enabled = False  # Disable ES for this request
        
        # ============================================
        # LAYER 1.5: MongoDB Fallback (if ES down)
        # ============================================
        if not self.es_enabled and self.mongo_repo:
            try:
                mongo_results = self.mongo_repo.search(
                    query=query,
                    limit=limit,
                    types=types
                )
                
                for item in mongo_results:
                    item["source"] = "mongodb"
                    # Convert ObjectId to string
                    if "_id" in item:
                        item["_id"] = str(item["_id"])
                    results.append(item)
                
                sources["mongodb"] = len(mongo_results)
                logger.debug(f"[MongoDB] Found {len(mongo_results)} results")
                
                # If enough results from MongoDB, return
                if len(mongo_results) >= self.MIN_ES_RESULTS:
                    logger.info(f"[AUTOCOMPLETE] MongoDB hit: {len(mongo_results)} results")
                    return self._build_response(results[:limit], sources, start_time)
                    
            except Exception as e:
                logger.warning(f"[MongoDB] Search failed: {e}")
        
        # ============================================
        # LAYER 2: Google Autocomplete API (Fallback)
        # ============================================
        current_count = len(results)
        needed = limit - current_count
        
        if needed > 0 and self.google_provider:
            # --- Anti-Abuse Check 1: Negative Cache ---
            if self._is_negative_cached(query):
                logger.info(f"[NEGATIVE_CACHE] Skipping Google API for known-empty query: '{query}'")
                return self._build_response(results[:limit], sources, start_time)
            
            # --- Anti-Abuse Check 2: Daily Quota ---
            quota_allowed, quota_current, quota_max = self._check_daily_quota()
            if not quota_allowed:
                logger.warning(
                    f"[QUOTA_EXCEEDED] Daily Google API quota exhausted: {quota_current}/{quota_max}. "
                    f"Returning cached results only."
                )
                return self._build_response(results[:limit], sources, start_time)
            
            try:
                google_results = self._call_google_autocomplete(
                    query=query,
                    session_token=session_token,
                    location=location,
                    types=types
                )
                
                # Increment quota counter AFTER successful call
                self._increment_daily_quota()
                
                # --- Anti-Abuse: Cache negative result ---
                if not google_results or len(google_results) == 0:
                    self._add_to_negative_cache(query)
                    logger.info(f"[GOOGLE] 0 results for '{query}', added to negative cache")
                    return self._build_response(results[:limit], sources, start_time)
                
                # Filter out duplicates (already in ES/MongoDB)
                existing_place_ids = {r.get("place_id") for r in results}
                new_results = [
                    r for r in google_results 
                    if r.get("place_id") not in existing_place_ids
                ]
                
                for item in new_results[:needed]:
                    item["source"] = "google"
                    results.append(item)
                
                sources["google"] = len(new_results[:needed])
                logger.debug(f"[Google] Found {len(new_results)} new results")
                
                # Cache Google results asynchronously
                if new_results:
                    self._cache_google_results(new_results)
                    
            except Exception as e:
                logger.error(f"[Google] Autocomplete failed: {e}")
        
        logger.info(
            f"[AUTOCOMPLETE] Total: {len(results)} | "
            f"ES: {sources['es']}, MongoDB: {sources['mongodb']}, Google: {sources['google']}"
        )
        
        return self._build_response(results[:limit], sources, start_time)
    
    def resolve(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a pending autocomplete item to full POI details.
        
        This is called when user CLICKS on a suggestion.
        
        Strategy:
        1. Check if already cached (status=cached) → return from MongoDB
        2. If pending → call Google Place Details API
        3. Cache full details to MongoDB/ES
        4. Update status to "cached"
        5. Increment click_count
        
        Args:
            place_id: Google Place ID
            
        Returns:
            Full POI details or None if not found
        """
        logger.info(f"[RESOLVE] Resolving place_id: {place_id}")
        
        # Check cache first
        if self.mongo_repo:
            cached = self.mongo_repo.get_by_place_id(place_id)
            
            if cached:
                # Increment click count
                self.mongo_repo.increment_click(place_id)
                if self.es_enabled and self.es_repo:
                    self.es_repo.increment_click(place_id)
                
                # If already cached, return full data
                if cached.get("status") == CacheStatus.CACHED.value:
                    logger.info(f"[RESOLVE] Cache hit for {place_id}")
                    return cached
        
        # Need to fetch from Google
        if not self.google_provider:
            logger.warning(f"[RESOLVE] No Google provider, cannot resolve {place_id}")
            return None
        
        try:
            # Call Google Place Details API
            details = self.google_provider.get_details(place_id)
            
            if not details:
                logger.warning(f"[RESOLVE] No details returned for {place_id}")
                return None
            
            # Update cache with full details
            if self.mongo_repo:
                lat = details.get("location", {}).get("latitude")
                lng = details.get("location", {}).get("longitude")
                
                self.mongo_repo.update_status(
                    place_id=place_id,
                    status=CacheStatus.CACHED.value,
                    lat=lat,
                    lng=lng
                )
            
            if self.es_enabled and self.es_repo:
                self.es_repo.update_status(
                    place_id=place_id,
                    status=CacheStatus.CACHED.value
                )
            
            logger.info(f"[RESOLVE] Resolved and cached {place_id}")
            return details
            
        except Exception as e:
            logger.error(f"[RESOLVE] Failed to resolve {place_id}: {e}")
            return None
    
    def _call_google_autocomplete(
        self,
        query: str,
        session_token: Optional[str] = None,
        location: Optional[Dict[str, float]] = None,
        types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Call Google Places Autocomplete API.
        
        Returns predictions in standardized format.
        """
        import requests
        import os
        
        api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_PLACES_API_KEY not configured")
        
        url = "https://places.googleapis.com/v1/places:autocomplete"
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key
        }
        
        body = {
            "input": query,
            "languageCode": "vi"
        }
        
        # Add session token if provided (for billing grouping)
        if session_token:
            body["sessionToken"] = session_token
        
        # Add location bias if provided
        if location:
            body["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": location.get("latitude"),
                        "longitude": location.get("longitude")
                    },
                    "radius": 50000.0  # 50km radius
                }
            }
        
        # Add type restrictions if provided
        if types:
            body["includedPrimaryTypes"] = types
        
        logger.debug(f"[Google API] Calling autocomplete for: '{query}'")
        
        response = requests.post(url, headers=headers, json=body, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        suggestions = data.get("suggestions", [])
        
        # Transform to standardized format
        results = []
        for suggestion in suggestions:
            place_prediction = suggestion.get("placePrediction", {})
            
            if not place_prediction:
                continue
            
            structured = place_prediction.get("structuredFormat", {})
            main_text = structured.get("mainText", {}).get("text", "")
            secondary_text = structured.get("secondaryText", {}).get("text", "")
            
            item = {
                "place_id": place_prediction.get("placeId", ""),
                "description": place_prediction.get("text", {}).get("text", ""),
                "main_text": main_text,
                "secondary_text": secondary_text,
                "types": place_prediction.get("types", []),
                "status": CacheStatus.PENDING.value
            }
            
            results.append(item)
        
        logger.info(f"[Google API] Got {len(results)} predictions for '{query}'")
        return results
    
    def _cache_google_results(self, items: List[Dict[str, Any]]) -> None:
        """
        Cache Google autocomplete results to MongoDB and ES.
        
        This runs after returning results to user (non-blocking if async).
        """
        for item in items:
            try:
                # Create AutocompleteItem
                cache_item = AutocompleteItem(
                    place_id=item["place_id"],
                    description=item.get("description", item.get("main_text", "")),
                    main_text=item.get("main_text", ""),
                    main_text_unaccented=AutocompleteItem._to_unaccented(item.get("main_text", "")),
                    secondary_text=item.get("secondary_text"),
                    types=item.get("types", []),
                    terms=[],  # Will be populated from Google response if available
                    status=CacheStatus.PENDING
                )
                
                cache_dict = cache_item.model_dump(mode='json')
                
                # Save to MongoDB (primary storage)
                if self.mongo_repo:
                    try:
                        self.mongo_repo.upsert(cache_dict)
                    except Exception as e:
                        logger.warning(f"[Cache] MongoDB upsert failed: {e}")
                
                # Index to ES (cache layer)
                if self.es_enabled and self.es_repo:
                    try:
                        self.es_repo.index_item(cache_dict)
                    except Exception as e:
                        logger.warning(f"[Cache] ES index failed: {e}")
                        
            except Exception as e:
                logger.warning(f"[Cache] Failed to cache item: {e}")
        
        logger.debug(f"[Cache] Cached {len(items)} items")
    
    def _build_response(
        self,
        results: List[Dict[str, Any]],
        sources: Dict[str, int],
        start_time: datetime
    ) -> Dict[str, Any]:
        """Build standardized response."""
        elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "suggestions": results,
            "total": len(results),
            "sources": sources,
            "query_time_ms": round(elapsed_ms, 2)
        }
    
    def _empty_response(self) -> Dict[str, Any]:
        """Return empty response."""
        return {
            "suggestions": [],
            "total": 0,
            "sources": {"es": 0, "google": 0, "mongodb": 0},
            "query_time_ms": 0
        }
    
    # ============================================
    # Admin Methods
    # ============================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "es_enabled": self.es_enabled,
            "mongodb_count": 0,
            "es_count": 0,
            "pending_count": 0,
            "cached_count": 0
        }
        
        if self.mongo_repo:
            stats["mongodb_count"] = self.mongo_repo.count()
            stats["pending_count"] = self.mongo_repo.count(status=CacheStatus.PENDING.value)
            stats["cached_count"] = self.mongo_repo.count(status=CacheStatus.CACHED.value)
        
        if self.es_enabled and self.es_repo:
            stats["es_count"] = self.es_repo.count()
        
        return stats
    
    def sync_mongodb_to_es(self, batch_size: int = 100) -> Dict[str, int]:
        """
        Sync all MongoDB items to ES.
        Use on startup or when ES index is rebuilt.
        """
        if not self.es_enabled or not self.es_repo or not self.mongo_repo:
            logger.warning("[Sync] ES or MongoDB not available")
            return {"synced": 0, "failed": 0}
        
        logger.info("[Sync] Starting MongoDB → ES sync")
        
        # Get all items from MongoDB
        # Note: For large datasets, implement pagination
        all_items = list(self.mongo_repo.get_popular(limit=10000))
        
        synced = 0
        failed = 0
        
        for item in all_items:
            try:
                # Convert ObjectId
                if "_id" in item:
                    del item["_id"]
                
                self.es_repo.index_item(item)
                synced += 1
            except Exception as e:
                logger.warning(f"[Sync] Failed to index: {e}")
                failed += 1
        
        logger.info(f"[Sync] Completed: {synced} synced, {failed} failed")
        return {"synced": synced, "failed": failed}
