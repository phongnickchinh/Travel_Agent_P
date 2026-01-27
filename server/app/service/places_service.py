"""
Places Service - Business Logic Layer
======================================

Purpose:
- Orchestrate POI operations across providers, MongoDB, and Elasticsearch
- Write-through cache strategy (Provider → MongoDB → Elasticsearch)
- Deduplication and data quality checks
- Cost-aware provider selection

Author: Travel Agent P Team
Date: November 27, 2025
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from ..providers.provider_factory import ProviderFactory
from ..providers.base_provider import BaseProvider
from ..repo.mongo.interfaces import POIRepositoryInterface
from ..repo.es.interfaces import ESPOIRepositoryInterface
from ..model.mongo.poi import POI, POISearchRequest
from ..utils.poi_dedupe import generate_dedupe_key, are_pois_duplicate
from ..core.clients.elasticsearch_client import ElasticsearchClient

logger = logging.getLogger(__name__)


class PlacesService:
    """
    Places Service - Write-Through Cache Orchestration
    
    Architecture:
        User Request
            ↓
        1. Check MongoDB Cache (fast)
            ↓ (if cache miss)
        2. Call Provider API (Google Places) - $$$ COST
            ↓
        3. Transform & Validate
            ↓
        4. Dedupe Check
            ↓
        5. Write-Through:
           - MongoDB (persistent cache)
           - Elasticsearch (search index)
            ↓
        6. Return Results
    
    Features:
    - Cost-aware caching (85% cache hit = 85% cost savings)
    - Smart deduplication across providers
    - Graceful ES degradation (fallback to MongoDB)
    - Background refresh for stale POIs
    - Bulk operations for efficiency
    
    Example:
        service = PlacesService()
        
        # Search with write-through cache
        results = service.search_and_cache(
            query="restaurants",
            location={"latitude": 16.0544, "longitude": 108.2428},
            radius_km=5
        )
        
        # Get by ID (from cache)
        poi = service.get_by_id("poi_mykhebeach")
        
        # Background job: refresh stale POIs
        service.refresh_stale_pois(limit=100)
    """
    
    def __init__(
        self, 
        poi_repo: POIRepositoryInterface,
        es_repo: ESPOIRepositoryInterface = None,
        cost_usage_repo = None
    ):
        """
        Initialize service with dependencies.
        
        Args:
            poi_repo: MongoDB POI repository (required)
            es_repo: Elasticsearch repository (optional, for degraded mode)
            cost_usage_repo: Cost usage repository (optional, for cost tracking)
        """
        self.poi_repo = poi_repo
        self.providers: List[BaseProvider] = ProviderFactory.get_providers()
        self.cost_usage_repo = cost_usage_repo
        
        # Elasticsearch (optional, graceful degradation)
        self.es_enabled = es_repo is not None and ElasticsearchClient.is_healthy()
        self.es_repo = es_repo if self.es_enabled else None
        
        if self.es_enabled:
            logger.info("[INFO] PlacesService initialized with Elasticsearch")
        else:
            logger.warning("[WARNING] PlacesService initialized WITHOUT Elasticsearch (degraded mode)")
        
        if not self.providers:
            logger.error("[ERROR] No providers available! Check API keys")
    
    def search_and_cache(
        self,
        query: str,
        location: Dict[str, float],
        radius_km: float = 5.0,
        min_results: int = 5,
        force_refresh: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search POIs with write-through cache (MongoDB → Provider API → Elasticsearch).
        4. Write-through to MongoDB + ES
        5. Return combined results
        
        Args:
            query: Search query (e.g., "restaurants", "beaches")
            location: {"latitude": float, "longitude": float}
            radius_km: Search radius in kilometers (default: 5)
            min_results: Minimum results to consider cache hit (default: 5)
            force_refresh: Skip cache and force API call (default: False)
            **kwargs: Additional filters (types, min_rating, price_level)
        
        Returns:
            {
                "results": [POI dicts],
                "total": int,
                "source": "cache" | "provider" | "hybrid",
                "cached_count": int,
                "new_count": int,
                "cost_saved": bool
            }
        
        Example:
            >>> results = service.search_and_cache(
            ...     "vietnamese restaurants",
            ...     {"latitude": 16.0544, "longitude": 108.2428},
            ...     radius_km=3,
            ...     min_rating=4.0
            ... )
            >>> print(f"Found {results['total']} POIs (source: {results['source']})")
        """
        logger.info(f"[SEARCH] Search request: query='{query}', location={location}, radius={radius_km}km")
        cached_results = []
        if not force_refresh:
            cached_results = self._search_cache(query, location, radius_km, **kwargs)
            
            if len(cached_results) >= min_results:
                logger.info(f"[INFO] Cache HIT: {len(cached_results)} POIs (saved API cost!)")
                return {
                    "results": cached_results,
                    "total": len(cached_results),
                    "source": "cache",
                    "cached_count": len(cached_results),
                    "new_count": 0,
                    "cost_saved": True
                }
            else:
                logger.info(f"[WARNING] Cache MISS: only {len(cached_results)} POIs (need {min_results})")
        provider_results = self._fetch_from_provider(query, location, radius_km, **kwargs)
        
        if not provider_results:
            logger.warning("[ERROR] Provider returned no results")
            return {
                "results": cached_results,
                "total": len(cached_results),
                "source": "cache",
                "cached_count": len(cached_results),
                "new_count": 0,
                "cost_saved": False
            }
        new_pois = self._write_through_cache(provider_results)
        combined = self._merge_results(cached_results, new_pois)
        
        logger.info(f"[INFO] Search completed: {len(combined)} total ({len(cached_results)} cached + {len(new_pois)} new)")
        
        return {
            "results": combined,
            "total": len(combined),
            "source": "hybrid" if cached_results else "provider",
            "cached_count": len(cached_results),
            "new_count": len(new_pois),
            "cost_saved": len(cached_results) > 0
        }
    
    def get_by_id(self, poi_id: str, include_fresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get POI by ID from cache.
        
        Args:
            poi_id: POI identifier
            include_fresh: If True and not in cache, try provider API
        
        Returns:
            POI dict or None
        
        Example:
            >>> poi = service.get_by_id("poi_mykhebeach")
            >>> print(poi['name'])
        """
        logger.info(f"[SEARCH] Get POI: {poi_id}")
        poi = self.poi_repo.get_by_id(poi_id)

        if poi:
            logger.info(f"[INFO] Cache HIT: {poi_id}")
            # If user requested fresh details or cached POI lacks detail fields, fetch provider details
            if include_fresh:
                try:
                    detailed = self.get_details(poi_id, force_update=True)
                    if detailed:
                        return detailed
                except Exception as e:
                    logger.warning(f"[WARNING] Failed to fetch provider details for {poi_id}: {e}")
            return poi

        # Not in cache: if include_fresh is True, attempt to ask provider if provider id is derivable
        if include_fresh:
            logger.info(f"[WARNING] Cache MISS: {poi_id}, trying provider...")
            # Try to find provider name/id by deducing from POI id (if provider id not present, cannot fetch)
            # For now, we cannot deduce provider id from poi_id alone; return None
        
        logger.warning(f"[ERROR] POI not found: {poi_id}")
        return None

    def get_details(self, poi_id: str, force_update: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get full POI details by ID, optionally forcing provider fetch and cache refresh.

        This method will:
        1. Load POI from MongoDB
        2. If provider info exists and force_update is True (or cached details missing), call provider.get_details
        3. Transform provider data, update MongoDB and ES, and return the updated POI
        """
        logger.info(f"[DETAILS] Get details for POI: {poi_id} (force_update={force_update})")
        poi = self.poi_repo.get_by_id(poi_id)
        if not poi:
            logger.warning(f"[DETAILS] POI {poi_id} not found in cache")
            return None

        provider_info = poi.get('provider', {})
        provider_name = provider_info.get('name')
        provider_id = provider_info.get('id')

        # If we don't know which provider or the provider id, we cannot fetch details
        if not provider_name or not provider_id:
            logger.warning(f"[DETAILS] No provider info available for {poi_id}")
            return poi

        if not force_update and poi.get('raw_data') and poi.get('images'):
            # We already have details cached
            return poi

        provider = self._get_provider_by_name(provider_name)
        if not provider:
            logger.warning(f"[DETAILS] Provider {provider_name} not available")
            return poi

        # Fetch details from provider
        try:
            detailed_data = provider.get_details(provider_id)
            if not detailed_data:
                logger.warning(f"[DETAILS] Provider returned no details for {provider_id}")
                return poi

            # Transform and upsert to MongoDB and ES
            transformed = self._transform_provider_data(detailed_data)
            # Maintain original poi_id if provider returns different dedupe
            transformed['poi_id'] = poi_id
            # Use upsert for safe write-through; to force update, call update directly with transformed payload
            try:
                # Force update ignoring staleness: use update to set transformed fields
                updates = {k: v for k, v in transformed.items() if k != 'poi_id'}
                updated = self.poi_repo.update(poi_id, updates)
                if updated is None:
                    logger.info(f"[DETAILS] Upsert fallback (insert) for {poi_id}")
                    # If update returned None, try upsert
                    self.poi_repo.upsert(POI(**transformed))
                else:
                    poi = updated
            except Exception as e:
                logger.error(f"[DETAILS] Failed to write details to MongoDB for {poi_id}: {e}")

            # Update Elasticsearch if enabled
            if self.es_enabled and self.es_repo:
                try:
                    self.es_repo.index_poi(poi_id, transformed)
                except Exception as e:
                    logger.warning(f"[DETAILS] ES indexing failed for {poi_id}: {e}")

            # Return the latest document (fetch to ensure consistency)
            return self.poi_repo.get_by_id(poi_id)

        except Exception as e:
            logger.error(f"[ERROR] Provider details fetch failed for {poi_id}: {e}")
            return poi
    
    def get_pois_for_planner(
        self,
        destination: str,
        location: Dict[str, float],
        interests: List[str] = None,
        min_results: int = 30,
        radius_km: float = 15.0
    ) -> List[Dict[str, Any]]:
        """
        Get POIs for planner prompt - core logic for plan generation.
        
        Flow:
        1. Search MongoDB by keyword (destination + interests) 
        2. Search nearby POIs from MongoDB
        3. If not enough, fetch from provider (Google Places)
        4. Dedupe results
        5. Return up to min_results POIs
        
        Args:
            destination: Destination city (e.g., "Da Nang")
            location: {"latitude": float, "longitude": float} - center point
            interests: User interests (e.g., ["beach", "food", "culture"])
            min_results: Minimum POIs to return (default: 30)
            radius_km: Search radius in km (default: 15)
            
        Returns:
            List of POI dicts (up to min_results)
            
        Example:
            >>> pois = places_service.get_pois_for_planner(
            ...     destination="Da Nang",
            ...     location={"latitude": 16.0544, "longitude": 108.2428},
            ...     interests=["beach", "culture", "food"],
            ...     min_results=30
            ... )
        """
        logger.info(
            f"[PLANNER] Fetching POIs for planner: destination={destination}, "
            f"interests={interests}, min_results={min_results}"
        )
        
        all_pois = []
        seen_dedupe_keys = set()
        interests = interests or []
        
        # --- Step 1: Search by destination keyword in MongoDB ---
        try:
            destination_pois = self._search_cache(
                query=destination,
                location=location,
                radius_km=radius_km,
                max_results=min_results
            )
            for poi in destination_pois:
                dedupe_key = poi.get('dedupe_key') or poi.get('poi_id')
                if dedupe_key and dedupe_key not in seen_dedupe_keys:
                    all_pois.append(poi)
                    seen_dedupe_keys.add(dedupe_key)
            logger.info(f"[PLANNER] Step 1 - Destination search: found {len(destination_pois)} POIs")
        except Exception as e:
            logger.error(f"[PLANNER] Destination search failed: {e}")
        
        # --- Step 2: Search by each interest keyword in MongoDB ---
        for interest in interests[:5]:  # Limit to 5 interests
            if len(all_pois) >= min_results:
                break
            try:
                interest_pois = self._search_cache(
                    query=interest,
                    location=location,
                    radius_km=radius_km,
                    max_results=min_results - len(all_pois)
                )
                for poi in interest_pois:
                    dedupe_key = poi.get('dedupe_key') or poi.get('poi_id')
                    if dedupe_key and dedupe_key not in seen_dedupe_keys:
                        all_pois.append(poi)
                        seen_dedupe_keys.add(dedupe_key)
                logger.info(f"[PLANNER] Step 2 - Interest '{interest}': found {len(interest_pois)} POIs")
            except Exception as e:
                logger.warning(f"[PLANNER] Interest search '{interest}' failed: {e}")
        
        # --- Step 3: Get nearby POIs from MongoDB (geo search) ---
        if len(all_pois) < min_results:
            try:
                nearby_pois = self.poi_repo.get_nearby(
                    lat=location.get('latitude', 0),
                    lng=location.get('longitude', 0),
                    radius_km=radius_km,
                    limit=min_results - len(all_pois)
                )
                for poi in nearby_pois:
                    dedupe_key = poi.get('dedupe_key') or poi.get('poi_id')
                    if dedupe_key and dedupe_key not in seen_dedupe_keys:
                        all_pois.append(poi)
                        seen_dedupe_keys.add(dedupe_key)
                logger.info(f"[PLANNER] Step 3 - Nearby search: found {len(nearby_pois)} POIs")
            except Exception as e:
                logger.warning(f"[PLANNER] Nearby search failed: {e}")
        
        # --- Step 4: If still not enough, fetch from provider ---
        if len(all_pois) < min_results:
            logger.info(f"[PLANNER] Step 4 - Fetching from provider (have {len(all_pois)}/{min_results})")
            
            # Search for destination + interests from provider
            search_queries = [destination] + interests[:3]
            
            for query in search_queries:
                if len(all_pois) >= min_results:
                    break
                try:
                    provider_results = self._fetch_from_provider(
                        query=query,
                        location=location,
                        radius_km=radius_km,
                        max_results=min_results - len(all_pois)
                    )
                    
                    if provider_results:
                        # Write through cache
                        cached_pois = self._write_through_cache(provider_results)
                        
                        for poi in cached_pois:
                            dedupe_key = poi.get('dedupe_key') or poi.get('poi_id')
                            if dedupe_key and dedupe_key not in seen_dedupe_keys:
                                all_pois.append(poi)
                                seen_dedupe_keys.add(dedupe_key)
                        
                        logger.info(f"[PLANNER] Provider query '{query}': added {len(cached_pois)} POIs")
                except Exception as e:
                    logger.warning(f"[PLANNER] Provider fetch '{query}' failed: {e}")
        
        # --- Step 5: Limit and return ---
        final_pois = all_pois[:min_results]
        logger.info(f"[PLANNER] Final POI count: {len(final_pois)} (requested: {min_results})")
        
        return final_pois
    
    def format_pois_for_prompt(self, pois: List[Dict[str, Any]], max_pois: int = 30) -> str:
        """
        Format POI list for LLM prompt.
        
        Args:
            pois: List of POI dicts
            max_pois: Maximum POIs to include
            
        Returns:
            Formatted string for LLM prompt
        """
        if not pois:
            return "No POI data available for this destination."
        
        lines = ["Available POIs for your itinerary (use poi_id exactly as shown):\n"]
        
        for i, poi in enumerate(pois[:max_pois], 1):
            poi_id = poi.get('poi_id', f'poi_{i}')
            name = poi.get('name', 'Unknown')
            name_en = poi.get('name_en', name)
            categories = poi.get('categories', [])
            if isinstance(categories, list):
                cat_str = ', '.join(categories[:3])
            else:
                cat_str = str(categories)
            
            rating = poi.get('ratings', {}).get('average') or poi.get('rating', 'N/A')
            price = poi.get('price_level', 'N/A')
            hours = poi.get('opening_hours') or poi.get('formatted_hours', 'N/A')
            if isinstance(hours, list):
                hours = hours[0] if hours else 'N/A'
            
            duration = poi.get('estimated_duration_minutes', 60)
            
            # Get description
            desc = poi.get('description', {})
            if isinstance(desc, dict):
                short_desc = desc.get('short', '')[:100]
            else:
                short_desc = str(desc)[:100] if desc else ''
            
            # Get coordinates
            loc = poi.get('location', {})
            coords = loc.get('coordinates', [0, 0]) if isinstance(loc, dict) else [0, 0]
            
            lines.append(
                f"{i}. poi_id: \"{poi_id}\"\n"
                f"   Name: {name_en} ({name})\n"
                f"   Categories: [{cat_str}]\n"
                f"   Rating: {rating} | Price: {price}\n"
                f"   Hours: {hours} | Duration: ~{duration} min\n"
                f"   Coordinates: [{coords[0]:.4f}, {coords[1]:.4f}]\n"
                f"   Description: {short_desc}\n"
            )
        
        return '\n'.join(lines)
    
    def refresh_stale_pois(self, limit: int = 100) -> Dict[str, Any]:
        """
        Background job: Refresh stale POIs from providers.
        
        Use case: Celery scheduled task to keep cache fresh
        
        Args:
            limit: Max number of POIs to refresh per run
        
        Returns:
            {
                "processed": int,
                "updated": int,
                "failed": int,
                "errors": [str]
            }
        
        Example:
            >>> # In Celery task
            >>> stats = service.refresh_stale_pois(limit=50)
            >>> logger.info(f"Refreshed {stats['updated']} POIs")
        """
        logger.info(f"[REFRESH] Starting background refresh (limit={limit})")
        
        # Get stale POIs from MongoDB
        stale_pois = self.poi_repo.get_stale_pois(limit=limit)
        
        if not stale_pois:
            logger.info("[INFO] No stale POIs to refresh")
            return {"processed": 0, "updated": 0, "failed": 0, "errors": []}
        
        logger.info(f"Found {len(stale_pois)} stale POIs")
        
        stats = {
            "processed": 0,
            "updated": 0,
            "failed": 0,
            "errors": []
        }
        
        for poi in stale_pois:
            try:
                provider_name = poi.get('provider', {}).get('name')
                provider_id = poi.get('provider', {}).get('id')
                
                if not provider_name or not provider_id:
                    logger.warning(f"[WARNING] POI {poi['poi_id']} missing provider info, skipping")
                    continue
                
                # Find matching provider
                provider = self._get_provider_by_name(provider_name)
                if not provider:
                    logger.warning(f"[WARNING] Provider '{provider_name}' not available")
                    continue
                fresh_data = provider.get_details(provider_id)
                
                if fresh_data:
                    # Update MongoDB
                    updates = self._extract_updates(fresh_data)
                    self.poi_repo.update(poi['poi_id'], updates)
                    
                    # Update ES (if enabled)
                    if self.es_enabled and self.es_repo:
                        self.es_repo.index_poi(poi['poi_id'], {**poi, **updates})
                    
                    stats["updated"] += 1
                    logger.info(f"[INFO] Refreshed: {poi['poi_id']}")
                else:
                    stats["failed"] += 1
                
                stats["processed"] += 1
            
            except Exception as e:
                logger.error(f"[ERROR] Failed to refresh {poi.get('poi_id', 'unknown')}: {e}")
                stats["failed"] += 1
                stats["errors"].append(str(e))
        
        logger.info(f"[INFO] Refresh completed: {stats['updated']}/{stats['processed']} updated")
        return stats
    
    def bulk_import(self, pois: List[Dict[str, Any]], skip_duplicates: bool = True) -> Dict[str, Any]:
        """
        Bulk import POIs (for seeding, migration, etc.)
        
        Args:
            pois: List of POI dicts
            skip_duplicates: Skip duplicate check (faster)
        
        Returns:
            {
                "total": int,
                "inserted": int,
                "updated": int,
                "skipped": int,
                "errors": int
            }
        
        Example:
            >>> # Import seed data
            >>> with open('seed_pois.json') as f:
            ...     pois = json.load(f)
            >>> stats = service.bulk_import(pois)
        """
        logger.info(f"[IMPORT] Bulk import: {len(pois)} POIs")
        poi_models = []
        for poi_dict in pois:
            try:
                poi = POI(**poi_dict)
                poi_models.append(poi)
            except Exception as e:
                logger.error(f"[ERROR] Invalid POI data: {e}")
        mongo_stats = self.poi_repo.bulk_upsert(poi_models)
        if self.es_enabled and self.es_repo:
            try:
                es_success, es_errors = self.es_repo.bulk_index([p.model_dump() for p in poi_models])
                logger.info(f"[INFO] ES indexed: {es_success} POIs ({es_errors} errors)")
            except Exception as e:
                logger.error(f"[ERROR] ES bulk index failed: {e}")
        
        logger.info(f"[INFO] Bulk import completed: {mongo_stats}")
        return mongo_stats
    
    # ========== PRIVATE HELPER METHODS ==========
    
    def _search_cache(
        self,
        query: str,
        location: Dict[str, float],
        radius_km: float,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Search MongoDB cache."""
        try:
            search_req = POISearchRequest(
                q=query,
                lat=location.get('latitude'),
                lng=location.get('longitude'),
                radius=radius_km,
                categories=kwargs.get('types'),
                min_rating=kwargs.get('min_rating'),
                price_level=kwargs.get('price_level'),
                page=1,
                limit=kwargs.get('max_results', 20)
            )
            
            result = self.poi_repo.search(search_req)
            return result.get('results', [])
        
        except Exception as e:
            logger.error(f"[ERROR] Cache search failed: {e}")
            return []
    
    def _fetch_from_provider(
        self,
        query: str,
        location: Dict[str, float],
        radius_km: float,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Fetch from provider API (Google Places) with minimal fields for cost saving."""
        if not self.providers:
            logger.error("[ERROR] No providers available")
            return []
        
        # Use first available provider (Google Places)
        provider = self.providers[0]
        
        try:
            logger.info(f"[COST] Calling {provider.get_provider_name()} API with MINIMAL fields (cost optimized)")
            
            # Extract max_results to avoid duplicate argument error
            max_results = kwargs.pop('max_results', 20)
            
            # Add field_mode='minimal' to minimize API cost (only id, displayName, location, photos)
            # User can override by passing field_mode='full' if detailed data is needed
            if 'field_mode' not in kwargs:
                kwargs['field_mode'] = 'minimal'
            
            results = provider.search(
                query=query,
                location=location,
                radius=int(radius_km * 1000),
                max_results=max_results,
                **kwargs
            )
            
            logger.info(f"[PROVIDER] Returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"[ERROR] Provider API failed: {e}")
            return []
    
    def _write_through_cache(self, provider_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Write-through to MongoDB + Elasticsearch.
        
        Returns list of successfully cached POIs.
        """
        if not provider_results:
            return []
        
        logger.info(f"[CACHE] Write-through cache: {len(provider_results)} POIs")
        poi_models = []
        for data in provider_results:
            try:
                poi_dict = self._transform_provider_data(data)
                poi = POI(**poi_dict)
                poi_models.append(poi)
            except Exception as e:
                logger.error(f"[ERROR] Failed to convert POI: {e}")
        
        if not poi_models:
            return []
        mongo_stats = self.poi_repo.bulk_upsert(poi_models)
        logger.info(f"[INFO] MongoDB: {mongo_stats}")
        if self.es_enabled and self.es_repo:
            try:
                poi_dicts = [p.model_dump(mode='json') for p in poi_models]
                success_count, error_count = self.es_repo.bulk_index(poi_dicts)
                logger.info(f"[INFO] Elasticsearch: {success_count} indexed ({error_count} errors)")
            except Exception as e:
                logger.error(f"[WARNING] ES indexing failed (non-critical): {e}")
        return [p.model_dump(mode='json') for p in poi_models]
    
    def _transform_provider_data(self, provider_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform provider-specific data to POI schema.
        
        Handles different provider formats (Google Places, TripAdvisor, etc.)
        """
        # (This is done in GooglePlacesProvider.transform_to_poi())
        if 'dedupe_key' not in provider_data:
            coords = provider_data.get('location', {}).get('coordinates', [0, 0])
            lng, lat = coords
            provider_data['dedupe_key'] = generate_dedupe_key(
                name=provider_data.get('name', 'Unknown'),
                latitude=lat,
                longitude=lng
            )
        if 'poi_id' not in provider_data:
            provider_data['poi_id'] = f"poi_{provider_data['dedupe_key']}"
        if 'metadata' not in provider_data:
            provider_data['metadata'] = {}
        
        provider_data['metadata']['created_at'] = datetime.utcnow()
        provider_data['metadata']['updated_at'] = datetime.utcnow()
        
        return provider_data
    
    def _merge_results(
        self,
        cached: List[Dict[str, Any]],
        new: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge cached and new results, removing duplicates.
        
        Prefers cached version (more complete after multiple fetches).
        """
        seen_keys = {poi.get('dedupe_key') for poi in cached if poi.get('dedupe_key')}
        merged = list(cached)
        for poi in new:
            dedupe_key = poi.get('dedupe_key')
            if dedupe_key not in seen_keys:
                merged.append(poi)
                seen_keys.add(dedupe_key)
        
        return merged
    
    def _get_provider_by_name(self, name: str) -> Optional[BaseProvider]:
        """Get provider by name."""
        for provider in self.providers:
            if provider.get_provider_name() == name:
                return provider
        return None
    
    def _extract_updates(self, fresh_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields to update from fresh provider data."""
        updates = {}
        
        if 'rating' in fresh_data:
            updates['ratings.average'] = fresh_data['rating']
        
        if 'user_ratings_total' in fresh_data:
            updates['ratings.count'] = fresh_data['user_ratings_total']
        
        if 'business_status' in fresh_data:
            updates['business_status'] = fresh_data['business_status']
        
        if 'formatted_phone_number' in fresh_data:
            updates['contact.phone'] = fresh_data['formatted_phone_number']
        
        if 'website' in fresh_data:
            updates['contact.website'] = fresh_data['website']
        updates['metadata.updated_at'] = datetime.utcnow()
        
        return updates
