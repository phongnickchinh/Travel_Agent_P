"""
Planner Service - Travel Itinerary Business Logic (Refactored)
===============================================================

Purpose:
- Orchestrate plan creation with LangChain
- Manage plan lifecycle (PENDING → PROCESSING → COMPLETED)
- Interface between controller and repository
- Handle errors and fallback logic
- Track API costs with real usage data
- Fetch POIs via repositories and providers (NO service-to-service imports)

Architecture:
- Uses repositories (POIRepository, PlaceDetailRepository) for MongoDB
- Uses providers (GooglePlacesProvider) directly for API calls
- NO imports from other services (except lc_chain)

Author: Travel Agent P Team
Date: December 24, 2025 - Refactored for clean architecture
"""

import logging
import time
from typing import List, Dict, Any, Optional

from ..model.mongo.plan import Plan, PlanStatusEnum, PlanCreateRequest, PlanUpdateRequest, PlanPatchRequest
from ..model.mongo.place_detail import PlaceDetail
from ..model.mongo.poi import POISearchRequest
from ..repo.mongo.plan_repository import PlanRepository
from ..repo.mongo.poi_repository import POIRepository
from ..repo.mongo.place_detail_repository import PlaceDetailRepository
from ..providers.places.google_places_provider import GooglePlacesProvider
from .lc_chain import TravelPlannerChain
from .cost_usage_service import CostUsageService
from ..utils.sanitization import sanitize_user_input

logger = logging.getLogger(__name__)

# Target POI count for itinerary generation
TARGET_POI_COUNT = 30
MIN_POI_COUNT = 10


class PlannerService:
    """
    Service layer for travel planning.
    
    Features:
    - Create plan (initialize with PENDING status)
    - Generate itinerary (LangChain orchestration)
    - Get user's plans
    - Update/regenerate plan
    - Delete plan
    - Fetch POIs using repositories and providers directly
    
    Workflow:
    1. User requests plan → create() → status=PENDING
    2. Celery task → generate_itinerary():
       a. Resolve destination place_id → get location
       b. Search nearby POIs in MongoDB first
       c. If not enough, fetch from Google API
       d. Format POIs for prompt
       e. Call LangChain
       f. status=COMPLETED
    3. Error → status=FAILED
    
    Architecture Notes:
    - NO service-to-service imports (clean dependency)
    - Uses repositories for data access
    - Uses providers for external APIs
    """
    
    def __init__(
        self, 
        plan_repository: Optional[PlanRepository] = None,
        poi_repository: Optional[POIRepository] = None,
        place_detail_repository: Optional[PlaceDetailRepository] = None,
        google_places_provider: Optional[GooglePlacesProvider] = None,
        cost_usage_service: Optional[CostUsageService] = None,
    ):
        """
        Initialize planner service with dependencies.
        
        Args:
            plan_repository: Plan repository (auto-created if None)
            poi_repository: POI repository for nearby search
            place_detail_repository: PlaceDetail repository for destination caching
            google_places_provider: Google Places API provider
            cost_usage_service: Cost tracking service (optional)
        """
        self.plan_repo = plan_repository or PlanRepository()
        self.poi_repo = poi_repository or POIRepository()
        self.place_detail_repo = place_detail_repository or PlaceDetailRepository()
        self.google_provider = google_places_provider or GooglePlacesProvider()
        self.cost_service = cost_usage_service
        
        logger.info("[INFO] PlannerService initialized with clean architecture (no service imports)")
    
    # ============================================
    # DESTINATION RESOLUTION
    # ============================================
    
    # Types that require Geocoding API for precise coordinates
    GEOCODE_REQUIRED_TYPES = {'locality', 'political', 'geocode', 'administrative_area_level_1', 
                              'administrative_area_level_2', 'country', 'sublocality'}
    
    def _resolve_destination(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Resolve destination place_id to full details with location.
        
        Strategy:
        1. Check PlaceDetailRepository (MongoDB cache)
        2. If miss, call Google Places API (Place Details)
        3. If type is locality/political/geocode → call Geocoding API for precise coords
        4. Cache result in PlaceDetailRepository
        
        Args:
            place_id: Google Place ID from autocomplete
            
        Returns:
            PlaceDetail dict with location, or None if failed
        """
        logger.info(f"[RESOLVE] Resolving destination place_id: {place_id}")
        
        # Step 1: Check cache
        cached = self.place_detail_repo.get_by_place_id(place_id)
        if cached:
            logger.info(f"[CACHE HIT] Destination found in cache: {cached.get('name')}")
            return cached
        
        # Step 2: Fetch from Google Places API (Place Details)
        logger.info(f"[CACHE MISS] Fetching destination from Google API: {place_id}")
        try:
            google_data = self.google_provider.get_details(place_id)
            
            if not google_data:
                logger.warning(f"[RESOLVE] Google API returned no data for {place_id}")
                return None
            
            # Step 3: Check if type requires Geocoding API
            types = google_data.get('types', [])
            # Also check raw_data for original types
            raw_types = google_data.get('raw_data', {}).get('types', [])
            all_types = set(types) | set(raw_types)
            
            needs_geocoding = bool(all_types & self.GEOCODE_REQUIRED_TYPES)
            
            if needs_geocoding:
                logger.info(f"[RESOLVE] Detected locality/political type {all_types}, calling Geocoding API")
                geocode_result = self.google_provider.geocode_by_place_id(place_id)
                
                if geocode_result:
                    # Update location in google_data
                    if 'location' not in google_data:
                        google_data['location'] = {}
                    
                    # Update coordinates from Geocoding API
                    google_data['location']['coordinates'] = [
                        geocode_result['longitude'],
                        geocode_result['latitude']
                    ]
                    google_data['_geocoded'] = True
                    logger.info(f"[RESOLVE] Updated coords from Geocoding: {geocode_result}")
                else:
                    logger.warning(f"[RESOLVE] Geocoding failed for {place_id}, using Place Details coords")
            
            # Step 4: Cache to MongoDB
            # Transform to PlaceDetail model
            place_detail = PlaceDetail.from_google_response(google_data)
            self.place_detail_repo.upsert(place_detail)
            
            logger.info(f"[RESOLVE] Cached destination: {place_detail.name} ({place_id})")
            
            return place_detail.to_dict()
            
        except Exception as e:
            logger.error(f"[RESOLVE] Failed to resolve destination {place_id}: {e}")
            return None
    
    # ============================================
    # POI FETCHING (MongoDB → Google fallback)
    # ============================================
    
    def _fetch_pois_for_plan(self, plan: Dict[str, Any], num_days: int) -> tuple:
        """
        Fetch POIs for a plan and format for LLM prompt.
        
        Strategy:
        1. Get destination location from plan
        2. Search nearby tourist POIs in MongoDB (POIRepository)
        3. If < TARGET_POI_COUNT, fetch more from Google API
        4. Cache new POIs to MongoDB
        5. Fetch accommodation POIs separately (hotels, resorts, hostels)
        6. Format both for LLM prompt
        
        Args:
            plan: Plan document from MongoDB
            num_days: Number of days in the plan
            
        Returns:
            Tuple of (poi_context, accommodation_context, poi_cache)
            - poi_context: Formatted tourist POIs for LLM prompt
            - accommodation_context: Formatted accommodations for LLM prompt
            - poi_cache: Dict mapping poi_id to POI data for post-processing
        """
        destination_place_id = plan.get('destination_place_id')
        destination_location = plan.get('destination_location')
        destination_name = plan.get('destination', 'Unknown')
        preferences = plan.get('preferences', {}) or {}
        interests = preferences.get('interests', [])
        target_poi_count = num_days*10
        
        # Get location from plan or resolve from place_id
        if destination_location:
            location = destination_location
        elif destination_place_id:
            resolved = self._resolve_destination(destination_place_id)
            if resolved:
                # Location format is GeoJSON: {"type": "Point", "coordinates": [lng, lat]}
                location_data = resolved.get('location', {})
                coords = location_data.get('coordinates', [])
                
                if len(coords) >= 2:
                    location = {
                        'latitude': coords[1],   # GeoJSON: [lng, lat]
                        'longitude': coords[0]
                    }
                else:
                    logger.warning(f"[WARN] Invalid coordinates format: {coords}")
                    return None
            else:
                logger.warning(f"[WARN] Could not resolve destination: {destination_place_id}")
                return None
        else:
            logger.warning("[WARN] No destination location available")
            return None
        
        logger.info(f"[POI_FETCH] Searching POIs near {destination_name}: {location}")
        
        all_pois = []
        
        # Step 1: Search MongoDB first
        try:
            mongo_pois = self._search_pois_mongodb(location, interests, limit=target_poi_count)
            all_pois.extend(mongo_pois)
            logger.info(f"[MongoDB] Found {len(mongo_pois)} cached POIs")
        except Exception as e:
            logger.warning(f"[MongoDB] POI search failed: {e}")
        
        # Step 2: If not enough, fetch from Google
        if len(all_pois) < target_poi_count:
            needed = target_poi_count - len(all_pois)
            logger.info(f"[Google] Need {needed} more POIs, calling Google API...")
            
            try:
                google_pois = self._search_pois_google(location, interests, limit=needed)
                
                # Cache new POIs to MongoDB
                for poi in google_pois:
                    self._cache_poi_to_mongodb(poi)
                
                all_pois.extend(google_pois)
                logger.info(f"[Google] Fetched and cached {len(google_pois)} new POIs")
            except Exception as e:
                logger.warning(f"[Google] POI search failed: {e}")
        
        # Check if we have enough POIs
        if len(all_pois) < MIN_POI_COUNT:
            logger.warning(f"[WARN] Only found {len(all_pois)} POIs (min: {MIN_POI_COUNT})")
            if len(all_pois) == 0:
                return (None, None, {})
        
        # --- STEP 3: Fetch Accommodation POIs (hotels, resorts, hostels) ---
        accommodation_pois = self._fetch_accommodations_for_plan(location, preferences, num_days)
        logger.info(f"[ACCOMMODATION] Found {len(accommodation_pois)} accommodation options")
        
        # Build POI cache for post-processing (featured_image, viewport)
        selected_pois = all_pois[:TARGET_POI_COUNT]
        poi_cache = {poi.get('poi_id', poi.get('place_id', '')): poi for poi in selected_pois}
        
        # Add accommodations to cache
        for acc in accommodation_pois:
            acc_id = acc.get('poi_id', acc.get('place_id', ''))
            if acc_id:
                poi_cache[acc_id] = acc
        
        # Format for LLM prompt (tourist POIs + accommodations)
        poi_context = self._format_pois_for_prompt(selected_pois, num_days*10)
        logger.info(f"{poi_context}")
        accommodation_context = self._format_accommodations_for_prompt(accommodation_pois)
        logger.info(f"[POI_FETCH] Formatted {len(selected_pois)} POIs + {len(accommodation_pois)} accommodations for prompt")
        
        return (poi_context, accommodation_context, poi_cache)
    
    def _search_pois_mongodb(
        self, 
        location: Dict[str, float], 
        interests: List[str],
        radius_km: float = 15.0,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Search POIs from MongoDB cache.
        
        Args:
            location: {'latitude': float, 'longitude': float}
            interests: User interests for filtering
            radius_km: Search radius in kilometers
            limit: Maximum results
            
        Returns:
            List of POI dicts
        """
        try:
            search_request = POISearchRequest(
                lat=location.get('latitude'),
                lng=location.get('longitude'),
                radius=radius_km,
                categories=interests if interests else None,
                limit=limit
            )
            
            result = self.poi_repo.search(search_request)
            return result.get('results', [])
            
        except Exception as e:
            logger.warning(f"[MongoDB] Search failed: {e}")
            return []
    
    def _search_pois_google(
        self, 
        location: Dict[str, float], 
        interests: List[str],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search POIs from Google Places API.
        
        Args:
            location: {'latitude': float, 'longitude': float}
            interests: User interests for search query
            limit: Maximum results
            
        Returns:
            List of POI dicts
        """
        results = []
        
        # Default queries if no interests
        # Use Google Places API (New) valid includedTypes from Table A
        # Ref: https://developers.google.com/maps/documentation/places/web-service/place-types
        if not interests:
            interests = ['tourist_attraction', 'restaurant', 'museum', 'park', 'beach']
        
        # Map user-friendly interest IDs to valid Google Place Types (Table A)
        # Frontend uses these IDs, backend maps to Google types
        type_mapping = {
            # Direct Google types (no mapping needed)
            'tourist_attraction': 'tourist_attraction',
            'restaurant': 'restaurant',
            'cafe': 'cafe',
            'museum': 'museum',
            'park': 'park',
            'beach': 'beach',
            'night_club': 'night_club',
            'bar': 'bar',
            'shopping_mall': 'shopping_mall',
            'spa': 'spa',
            'historical_landmark': 'historical_landmark',
            'amusement_park': 'amusement_park',
            'zoo': 'zoo',
            'aquarium': 'aquarium',
            # User-friendly aliases -> Google types
            'culture': 'museum',
            'food': 'restaurant',
            'dining': 'restaurant',
            'nature': 'park',
            'nightlife': 'night_club',
            'shopping': 'shopping_mall',
            'relaxation': 'spa',
            'history': 'historical_landmark',
            'adventure': 'amusement_park',
            'family': 'amusement_park',
            'photography': 'tourist_attraction',
            'romantic': 'restaurant',
            'hotel': 'lodging',
            'lodging': 'lodging',
        }
        
        # Convert interests to valid Google types
        valid_types = []
        for interest in interests[:5]:  # Limit to 5 types
            mapped_type = type_mapping.get(interest.lower(), interest)
            if mapped_type not in valid_types:
                valid_types.append(mapped_type)
        
        # Search by each type (Google API accepts multiple types but works better with specific ones)
        for place_type in valid_types:
            try:
                # Use nearby_search for geo-based results
                pois = self.google_provider.nearby_search(
                    location=location,
                    radius=15000,  # 15km
                    types=[place_type],
                    max_results=min(limit // len(valid_types) + 1, 20)
                )
                
                results.extend(pois)
                
                if len(results) >= limit:
                    break
                    
            except Exception as e:
                logger.warning(f"[Google] Search for '{place_type}' failed: {e}")
                continue
        
        return results[:limit]
    
    # ============================================
    # ACCOMMODATION FETCHING (Hotels, Resorts, Hostels)
    # ============================================
    
    # Accommodation types from Google Places API Table A
    ACCOMMODATION_TYPES = ['lodging', 'hotel', 'resort_hotel', 'extended_stay_hotel', 
                           'motel', 'hostel', 'bed_and_breakfast', 'guest_house']
    
    def _fetch_accommodations_for_plan(
        self, 
        location: Dict[str, float], 
        preferences: Dict[str, Any],
        num_days: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch accommodation POIs (hotels, resorts, hostels) for the plan.
        
        Accommodations are fetched separately from tourist POIs because:
        1. Different category with different selection criteria
        2. Need check-in/check-out time consideration
        3. May need to change based on next day's cluster location
        
        Args:
            location: Destination location {'latitude': float, 'longitude': float}
            preferences: User preferences including budget_level
            num_days: Number of days (affects accommodation count needed)
            
        Returns:
            List of accommodation POI dicts
        """
        accommodations = []
        budget_level = preferences.get('budget_level', 'medium')
        
        # Calculate how many accommodations to fetch (1-2 options per price tier)
        target_count = max(5, num_days + 2)  # At least 5 options
        
        # Step 1: Search MongoDB for cached accommodations
        try:
            mongo_accommodations = self._search_accommodations_mongodb(
                location, 
                budget_level,
                limit=target_count
            )
            accommodations.extend(mongo_accommodations)
            logger.info(f"[ACCOMMODATION] Found {len(mongo_accommodations)} cached accommodations in MongoDB")
        except Exception as e:
            logger.warning(f"[ACCOMMODATION] MongoDB search failed: {e}")
        
        # Step 2: If not enough, fetch from Google
        if len(accommodations) < target_count:
            needed = target_count - len(accommodations)
            logger.info(f"[ACCOMMODATION] Need {needed} more, calling Google API...")
            
            try:
                google_accommodations = self._search_accommodations_google(
                    location,
                    limit=needed
                )
                
                # Cache new accommodations to MongoDB
                for acc in google_accommodations:
                    self._cache_poi_to_mongodb(acc)
                
                accommodations.extend(google_accommodations)
                logger.info(f"[ACCOMMODATION] Fetched {len(google_accommodations)} from Google")
            except Exception as e:
                logger.warning(f"[ACCOMMODATION] Google search failed: {e}")
        
        return accommodations[:target_count]
    
    def _search_accommodations_mongodb(
        self, 
        location: Dict[str, float],
        budget_level: str,
        radius_km: float = 20.0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search accommodations from MongoDB cache.
        
        Args:
            location: {'latitude': float, 'longitude': float}
            budget_level: 'low', 'medium', 'high', 'luxury'
            radius_km: Search radius
            limit: Maximum results
            
        Returns:
            List of accommodation POI dicts
        """
        try:
            # Map budget level to price levels
            price_level_filter = {
                'low': [0, 1],      # Free, Budget-friendly
                'medium': [1, 2],   # Budget-friendly, Moderate
                'high': [2, 3],     # Moderate, Premium
                'luxury': [3, 4]    # Premium, Luxury
            }.get(budget_level, [1, 2])
            
            search_request = POISearchRequest(
                lat=location.get('latitude'),
                lng=location.get('longitude'),
                radius=radius_km,
                categories=self.ACCOMMODATION_TYPES,
                limit=limit
            )
            
            result = self.poi_repo.search(search_request)
            accommodations = result.get('results', [])
            
            # Filter by price level if available
            filtered = [
                acc for acc in accommodations
                if acc.get('price_level', 2) in price_level_filter
            ]
            
            return filtered if filtered else accommodations[:limit]
            
        except Exception as e:
            logger.warning(f"[ACCOMMODATION] MongoDB search failed: {e}")
            return []
    
    def _search_accommodations_google(
        self, 
        location: Dict[str, float],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search accommodations from Google Places API.
        
        Uses accommodation-specific types: lodging, hotel, resort_hotel, etc.
        
        Args:
            location: {'latitude': float, 'longitude': float}
            limit: Maximum results
            
        Returns:
            List of accommodation POI dicts
        """
        results = []
        
        # Search using primary accommodation types
        primary_types = ['lodging', 'hotel']  # Start with main types
        
        for place_type in primary_types:
            try:
                pois = self.google_provider.nearby_search(
                    location=location,
                    radius=20000,  # 20km for accommodations
                    types=[place_type],
                    max_results=min(limit, 10)
                )
                
                results.extend(pois)
                
                if len(results) >= limit:
                    break
                    
            except Exception as e:
                logger.warning(f"[ACCOMMODATION] Google search for '{place_type}' failed: {e}")
                continue
        
        return results[:limit]
    
    def _format_accommodations_for_prompt(self, accommodations: List[Dict[str, Any]]) -> str:
        """
        Format accommodation list for LLM prompt.
        
        Includes location coordinates for distance calculation to POI clusters.
        
        Args:
            accommodations: List of accommodation POI dicts
            
        Returns:
            Formatted string for LLM context
        """
        if not accommodations:
            return ""
        
        lines = []
        lines.append("\n=== AVAILABLE ACCOMMODATIONS (Hotels, Resorts, Hostels) ===\n")
        lines.append("NOTE: Select accommodations strategically based on proximity to POI clusters.")
        lines.append("      Consider changing accommodation if next day's cluster is far away.\n")
        
        for i, acc in enumerate(accommodations, 1):
            # Extract location
            location = acc.get('location', {})
            if isinstance(location, dict):
                coords = location.get('coordinates', [])
                if len(coords) >= 2:
                    lat, lng = coords[1], coords[0]  # GeoJSON format
                else:
                    lat, lng = 0, 0
            else:
                lat, lng = 0, 0
            
            # Extract rating and price
            rating = acc.get('rating', 0)
            reviews_count = acc.get('user_ratings_total', acc.get('total_reviews', 0))
            price_level = acc.get('price_level', 2)
            price_indicator = self._format_price_level(price_level)
            
            # Extract reviews summary if available
            reviews_summary = self._extract_reviews_summary(acc)
            
            acc_id = acc.get('poi_id', acc.get('place_id', 'N/A'))
            name = acc.get('name', 'Unknown')
            address = acc.get('address', acc.get('vicinity', 'N/A'))
            types = acc.get('types', [])[:3]
            
            lines.append(f"{i}. {name}")
            lines.append(f"   ID: {acc_id}")
            lines.append(f"   Location: ({lat:.6f}, {lng:.6f})")
            lines.append(f"   Address: {address}")
            lines.append(f"   Types: {', '.join(types)}")
            lines.append(f"   Rating: ★{rating:.1f} ({reviews_count} reviews) | Price: {price_indicator}")
            if reviews_summary:
                lines.append(f"   Reviews: {reviews_summary}")
            lines.append("")
        
        lines.append(f"=== TOTAL: {len(accommodations)} accommodations available ===")
        
        return "\n".join(lines)
    
    def _cache_poi_to_mongodb(self, poi_data: Dict[str, Any]) -> bool:
        """
        Cache POI data to MongoDB using upsert (insert or update if stale).
        
        Args:
            poi_data: Standardized POI dict from Google API (already transformed)
            
        Returns:
            True if POI was cached successfully
        """
        try:
            from ..model.mongo.poi import POI
            
            # Validate that poi_data has required fields
            poi_id = poi_data.get('poi_id')
            if not poi_id:
                logger.warning(f"[CACHE] POI missing poi_id, skipping cache: {poi_data.get('name', 'Unknown')}")
                return False
            
            # Create POI model from dict (this validates the schema)
            try:
                poi_model = POI(**poi_data)
            except Exception as validation_error:
                logger.warning(f"[CACHE] POI validation failed for {poi_id}: {validation_error}")
                return False
            
            # Upsert to MongoDB (insert new or update if stale)
            result = self.poi_repo.upsert(poi_model)
            
            operation = result.get('_operation', 'unknown')
            if operation == 'inserted':
                logger.info(f"[CACHE] ✓ Inserted new POI: {poi_id} - {poi_data.get('name')}")
                return True
            elif operation == 'updated':
                logger.info(f"[CACHE] ↻ Updated stale POI: {poi_id} - {poi_data.get('name')}")
                return True
            elif operation == 'skipped':
                logger.debug(f"[CACHE] ○ POI fresh, skipped: {poi_id}")
                return True
            else:
                logger.warning(f"[CACHE] Unknown operation: {operation}")
                return False
            
        except Exception as e:
            logger.warning(f"[CACHE] Failed to cache POI: {e}")
            return False
    
    def _format_pois_for_prompt(self, pois: List[Dict[str, Any]], max_pois: int = 30) -> str:
        """
        Format POI list for LLM prompt with coordinates, reviews, and pricing.
        POIs are grouped by geographic clusters for optimal travel planning.
        
        Args:
            pois: List of POI dicts
            max_pois: Maximum POIs to include
            
        Returns:
            Formatted string for LLM context with clusters, reviews, pricing
        """
        if not pois:
            return ""
        
        # Cluster POIs by geographic proximity before formatting
        # Use 5km radius to group POIs into larger "day-trip" capable areas
        # Target: Create clusters equal to typical trip duration (inferred from POI count)
        # Heuristic: ~3-4 POIs per day → target_clusters = max_pois / 4
        target_clusters = max(3, min(7, max_pois // 4))  # Between 3-7 clusters
        clustered_pois = self._cluster_pois_by_location(
            pois[:max_pois], 
            radius_km=5.0,
            target_clusters=target_clusters
        )
        
        lines = []
        lines.append("=== AVAILABLE PLACES OF INTEREST (Grouped by Area) ===\n")
        lines.append("NOTE: POIs are pre-grouped by geographic proximity (Clusters).")
        lines.append("      - You can visit multiple clusters in one day if needed to fill the schedule.")
        lines.append("      - If a cluster is small, combine it with nearby clusters.\n")
        
        poi_index = 1
        for cluster_id, cluster_pois in clustered_pois.items():
            cluster_center = self._calculate_cluster_center(cluster_pois)
            lines.append(f"\n--- CLUSTER {cluster_id}: Area around ({cluster_center[0]:.4f}, {cluster_center[1]:.4f}) ---")
            lines.append(f"    Contains {len(cluster_pois)} POIs within ~2km radius\n")
            
            for poi in cluster_pois:
                formatted_poi = self._format_single_poi(poi, poi_index)
                lines.append(formatted_poi)
                poi_index += 1
        
        lines.append(f"\n=== TOTAL: {min(len(pois), max_pois)} places in {len(clustered_pois)} geographic clusters ===")
        lines.append("\nIMPORTANT:")
        lines.append("- Prioritize POIs from the same cluster on the same day")
        lines.append("- Consider review ratings and sentiments when selecting must-visit places")
        lines.append("- Match price levels to user's budget preference")
        
        return "\n".join(lines)
    
    def _format_single_poi(self, poi: Dict[str, Any], index: int) -> str:
        """
        Format a single POI with reviews and pricing info.
        Excludes google_data to reduce LLM input size.
        
        Args:
            poi: POI dict
            index: Display index
            
        Returns:
            Formatted string for single POI
        """
        name = poi.get('name', 'Unknown')
        categories = poi.get('categories', [])
        rating = poi.get('ratings', {}).get('average', 'N/A')
        review_count = poi.get('ratings', {}).get('count', 0)
        description = poi.get('description', {}).get('short', '')
        poi_id = poi.get('poi_id', f'poi_{index}')
        
        # Extract coordinates
        location = poi.get('location', {})
        coords = location.get('coordinates', [None, None])
        lat = coords[1] if len(coords) > 1 else None
        lng = coords[0] if len(coords) > 0 else None
        
        # Extract pricing info
        pricing = poi.get('pricing', {})
        price_level = pricing.get('level', 'N/A')
        avg_cost = pricing.get('average_cost_per_person', {})
        price_display = self._format_price_level(price_level, avg_cost)
        
        # Extract reviews from google_data (prioritize) or main ratings
        reviews_summary = self._extract_reviews_summary(poi)
        
        # Build POI line
        line = f"{index}. [{poi_id}] {name}"
        
        if lat and lng:
            line += f" @({lat:.5f}, {lng:.5f})"
        
        if categories:
            line += f" ({', '.join(categories[:2])})"
        
        if rating and rating != 'N/A':
            line += f" ★{rating}"
            if review_count:
                line += f" ({review_count} reviews)"
        
        # Add pricing
        if price_display:
            line += f" | {price_display}"
        
        # Add description
        if description:
            line += f"\n   📝 {description[:120]}"
        
        # Add review highlights
        if reviews_summary:
            line += f"\n   💬 Reviews: {reviews_summary}"
        
        return line
    
    def _extract_reviews_summary(self, poi: Dict[str, Any]) -> str:
        """
        Extract review summary from POI data.
        Prioritizes google_data.reviews if available.
        
        Args:
            poi: POI dict
            
        Returns:
            Summarized review string (max 150 chars)
        """
        reviews = []
        
        # Try google_data.reviews first
        google_data = poi.get('google_data', {})
        if google_data:
            google_reviews = google_data.get('reviews', [])
            if google_reviews:
                for review in google_reviews[:3]:  # Max 3 reviews
                    text = review.get('text', '')
                    rating = review.get('rating', 0)
                    if text and len(text) > 20:
                        # Truncate long reviews
                        short_text = text[:80] + '...' if len(text) > 80 else text
                        reviews.append(f"({rating}★) {short_text}")
        
        if not reviews:
            # Fallback: try main reviews field
            main_reviews = poi.get('reviews', [])
            if main_reviews:
                for review in main_reviews[:3]:
                    text = review.get('text', '')
                    rating = review.get('rating', 0)
                    if text:
                        short_text = text[:80] + '...' if len(text) > 80 else text
                        reviews.append(f"({rating}★) {short_text}")
        
        if reviews:
            return ' | '.join(reviews[:2])  # Max 2 reviews in output
        return ""
    
    def _format_price_level(self, price_level: str, avg_cost: Optional[Dict] = None) -> str:
        """
        Format price level to human-readable string.
        
        Args:
            price_level: Price level enum value
            avg_cost: Average cost dict
            
        Returns:
            Formatted price string
        """
        level_map = {
            'free': '💰 Free',
            'inexpensive': '💰 Budget-friendly',
            'moderate': '💰💰 Moderate',
            'expensive': '💰💰💰 Premium',
            'very_expensive': '💰💰💰💰 Luxury'
        }
        
        display = level_map.get(str(price_level).lower(), '')
        
        if avg_cost:
            amount = avg_cost.get('amount', 0)
            currency = avg_cost.get('currency', 'VND')
            if amount:
                display += f" (~{amount:,.0f} {currency}/person)"
        
        return display
    
    def _cluster_pois_by_location(
        self, 
        pois: List[Dict[str, Any]], 
        radius_km: float = 2.0,
        target_clusters: Optional[int] = None
    ) -> Dict[int, List[Dict]]:
        """
        Cluster POIs by geographic proximity using BFS + Merge Small Clusters.
        
        Algorithm:
        1. Build adjacency list of POIs within radius_km
        2. Use BFS to find connected components (transitive: A→B→C all in same cluster)
        3. If target_clusters specified and actual_clusters > target:
           - Merge smallest cluster with nearest cluster
           - Repeat until len(clusters) == target_clusters
        
        Example:
            POI A at (16.0544, 108.2428)
            POI B at (16.0548, 108.2430) - 50m from A
            POI C at (16.0552, 108.2432) - 50m from B, 100m from A
            With radius=2km → All in same cluster (transitive)
        
        Args:
            pois: List of POI dicts with location data
            radius_km: Clustering radius in kilometers (default: 2.0)
            target_clusters: Target number of clusters (e.g., num_days). If None, no merging.
            
        Returns:
            Dict of {cluster_id: [POI, POI, ...]}
        """
        if not pois:
            return {}
        
        # Extract coordinates from POIs
        poi_nodes = []
        for i, poi in enumerate(pois):
            location = poi.get('location', {})
            coords = location.get('coordinates', [None, None])
            
            # Check for valid coordinates [lng, lat]
            is_valid = False
            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                lng, lat = coords[0], coords[1]
                if (isinstance(lng, (int, float)) and isinstance(lat, (int, float))):
                    is_valid = True
            
            if is_valid:
                poi_nodes.append({
                    'index': i,
                    'poi': poi,
                    'lat': float(coords[1]),
                    'lng': float(coords[0]),
                    'cluster': -1  # -1 means unassigned
                })
            else:
                # POI without valid coords goes to default cluster 0
                poi_nodes.append({
                    'index': i,
                    'poi': poi,
                    'lat': None,
                    'lng': None,
                    'cluster': 0
                })
        
        # Transitive clustering (BFS/Connected Components)
        cluster_id = 1
        degree_threshold = radius_km / 111.0  # Approximate degrees per km
        
        # Get indices of valid POIs that need clustering
        valid_indices = [i for i, p in enumerate(poi_nodes) if p['cluster'] == -1]
        
        for i in valid_indices:
            if poi_nodes[i]['cluster'] != -1:
                continue
                
            # Start new cluster
            current_cluster = cluster_id
            cluster_id += 1
            poi_nodes[i]['cluster'] = current_cluster
            
            # BFS queue with visited tracking to avoid duplicate processing
            queue = [i]
            visited = {i}  # Track nodes already added to queue
            
            while queue:
                curr_idx = queue.pop(0)
                curr_node = poi_nodes[curr_idx]
                
                # Check against all other unassigned valid POIs
                for neighbor_idx in valid_indices:
                    # Skip if already visited or already in a cluster
                    if neighbor_idx in visited:
                        continue
                    
                    neighbor = poi_nodes[neighbor_idx]
                    
                    if neighbor['cluster'] != -1:
                        continue
                        
                    # Calculate distance
                    lat_diff = abs(curr_node['lat'] - neighbor['lat'])
                    lng_diff = abs(curr_node['lng'] - neighbor['lng'])
                    
                    if lat_diff <= degree_threshold and lng_diff <= degree_threshold:
                        # Assign cluster immediately
                        neighbor['cluster'] = current_cluster
                        # Add to queue for further expansion
                        queue.append(neighbor_idx)
                        # Mark as visited to prevent duplicate processing
                        visited.add(neighbor_idx)
        
        # Group POIs by cluster
        clusters = {}
        for node in poi_nodes:
            cid = node['cluster']
            if cid not in clusters:
                clusters[cid] = []
            clusters[cid].append(node['poi'])
        
        logger.info(f"[CLUSTERING] BFS created {len(clusters)} clusters from {len(pois)} POIs (radius={radius_km}km)")
        
        # --- STEP 2: Merge small clusters if target_clusters specified ---
        if target_clusters and len(clusters) > target_clusters:
            logger.info(f"[MERGE] Merging {len(clusters)} clusters down to {target_clusters} target clusters")
            clusters = self._merge_small_clusters(clusters, poi_nodes, target_clusters)
        
        return clusters
    
    def _merge_small_clusters(
        self, 
        clusters: Dict[int, List[Dict]], 
        poi_nodes: List[Dict],
        target_clusters: int
    ) -> Dict[int, List[Dict]]:
        """
        Merge small clusters with nearest clusters until reaching target count.
        
        Strategy:
        1. Find smallest cluster (by POI count)
        2. Find nearest cluster to it (by cluster center distance)
        3. Merge smallest into nearest
        4. Repeat until len(clusters) == target_clusters
        
        Args:
            clusters: Current clusters dict {cluster_id: [POI list]}
            poi_nodes: Original POI nodes with coordinates
            target_clusters: Desired number of clusters
            
        Returns:
            Merged clusters dict
        """
        while len(clusters) > target_clusters:
            # Find smallest cluster
            smallest_id = min(clusters.keys(), key=lambda cid: len(clusters[cid]))
            smallest_cluster = clusters[smallest_id]
            
            if len(clusters) == 1:
                break  # Safety: only 1 cluster left
            
            # Calculate center of smallest cluster
            smallest_center = self._calculate_cluster_center(smallest_cluster)
            
            # Find nearest cluster (excluding smallest)
            min_distance = float('inf')
            nearest_id = None
            
            for cluster_id, cluster_pois in clusters.items():
                if cluster_id == smallest_id:
                    continue
                
                # Calculate center of candidate cluster
                candidate_center = self._calculate_cluster_center(cluster_pois)
                
                # Distance between centers (Euclidean in lat/lng degrees)
                distance = (
                    (smallest_center[0] - candidate_center[0]) ** 2 +
                    (smallest_center[1] - candidate_center[1]) ** 2
                ) ** 0.5
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_id = cluster_id
            
            if nearest_id is None:
                logger.warning(f"[MERGE] Could not find nearest cluster for cluster {smallest_id}")
                break
            
            # Merge smallest into nearest
            clusters[nearest_id].extend(smallest_cluster)
            del clusters[smallest_id]
            
            logger.info(
                f"[MERGE] Merged cluster {smallest_id} ({len(smallest_cluster)} POIs) "
                f"into cluster {nearest_id} (distance={min_distance*111:.2f}km). "
                f"Remaining: {len(clusters)} clusters"
            )
        
        # Re-index clusters to be sequential (1, 2, 3, ...)
        sorted_ids = sorted(clusters.keys())
        reindexed = {i+1: clusters[old_id] for i, old_id in enumerate(sorted_ids)}
        
        logger.info(f"[MERGE] Final: {len(reindexed)} balanced clusters")
        return reindexed
    
    def _calculate_cluster_center(self, cluster_pois: List[Dict[str, Any]]) -> tuple:
        """
        Calculate the geographic center of a cluster.
        
        Args:
            cluster_pois: List of POIs in the cluster
            
        Returns:
            Tuple (lat, lng) of cluster center
        """
        valid_coords = []
        for poi in cluster_pois:
            location = poi.get('location', {})
            coords = location.get('coordinates', [])
            if len(coords) >= 2 and coords[0] is not None:
                valid_coords.append((coords[1], coords[0]))  # (lat, lng)
        
        if not valid_coords:
            return (0.0, 0.0)
        
        avg_lat = sum(c[0] for c in valid_coords) / len(valid_coords)
        avg_lng = sum(c[1] for c in valid_coords) / len(valid_coords)
        
        return (avg_lat, avg_lng)
    
    def _post_process_itinerary(
        self, 
        itinerary: List[Dict[str, Any]], 
        poi_cache: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Post-process LLM-generated itinerary to populate featured_image and viewport.
        
        Args:
            itinerary: Raw itinerary from LLM
            poi_cache: Dict mapping poi_id to POI data
            
        Returns:
            Enhanced itinerary with featured_image and viewport populated
        """
        import random
        
        for day_plan in itinerary:
            poi_ids = day_plan.get('poi_ids', [])
            if not poi_ids:
                continue
            
            # Collect coordinates for viewport calculation
            coords_list = []
            day_pois = []
            
            for poi_id in poi_ids:
                poi = poi_cache.get(poi_id)
                if not poi:
                    continue
                day_pois.append(poi)
                
                # Extract coordinates (GeoJSON format: [lng, lat])
                location = poi.get('location', {})
                coords = location.get('coordinates', [])
                if len(coords) >= 2 and coords[0] is not None:
                    coords_list.append({
                        'lat': coords[1],
                        'lng': coords[0]
                    })
            
            # --- Populate featured_images (one per POI) ---
            featured_images = []
            types_list = []  # NEW: Populate types array for each POI
            for poi in day_pois:
                images = poi.get('images', [])
                featured_url = None
                
                if images:
                    # Pick first image from POI
                    if isinstance(images[0], dict):
                        # Image objects with url field
                        image_urls = [img.get('url') for img in images if img.get('url')]
                    else:
                        # Direct URLs
                        image_urls = [img for img in images if img]
                    
                    if image_urls:
                        featured_url = image_urls[0]  # Use first image
                
                featured_images.append(featured_url)
                
                # Extract categories/types from POI
                poi_types = poi.get('categories', [])
                types_list.append(poi_types if poi_types else [])
            
            day_plan['featured_images'] = featured_images
            day_plan['types'] = types_list  # Add types to day plan
            
            # --- Populate viewport ---
            if coords_list:
                # Calculate bounding box
                lats = [c['lat'] for c in coords_list]
                lngs = [c['lng'] for c in coords_list]
                
                # Add padding (about 10% extra on each side)
                lat_padding = (max(lats) - min(lats)) * 0.1 or 0.01
                lng_padding = (max(lngs) - min(lngs)) * 0.1 or 0.01
                
                day_plan['viewport'] = {
                    'northeast': {
                        'lat': max(lats) + lat_padding,
                        'lng': max(lngs) + lng_padding
                    },
                    'southwest': {
                        'lat': min(lats) - lat_padding,
                        'lng': min(lngs) - lng_padding
                    }
                }
                
                # Calculate center if not provided by LLM
                if not day_plan.get('location'):
                    day_plan['location'] = [
                        sum(lats) / len(lats),
                        sum(lngs) / len(lngs)
                    ]
        
        return itinerary
    
    # ============================================
    # PLAN CRUD OPERATIONS
    # ============================================
    
    def create_plan(self, user_id: str, request: PlanCreateRequest) -> Dict[str, Any]:
        """
        Create new plan with PENDING status.
        
        Args:
            user_id: User identifier
            request: PlanCreateRequest payload
            
        Returns:
            Created plan dict
        """
        try:
            # Resolve destination to get location and photo_references
            destination_location = None
            thumbnail_url = None
            
            if request.destination_place_id:
                resolved = self._resolve_destination(request.destination_place_id)
                if resolved:
                    # Location format is GeoJSON: {"type": "Point", "coordinates": [lng, lat]}
                    location_data = resolved.get('location', {})
                    coords = location_data.get('coordinates', [])
                    
                    if len(coords) >= 2:
                        destination_location = {
                            'latitude': coords[1],   # GeoJSON: [lng, lat]
                            'longitude': coords[0]
                        }
                    
                    # Try to get thumbnail from first photo
                    photo_references = resolved.get('photo_references', [])
                    if photo_references:
                        try:
                            # Use first photo as thumbnail
                            first_photo = photo_references[0]
                            logger.info(f"[THUMBNAIL] Getting photo URL for destination: {first_photo}")
                            
                            # Get direct Google Places photo URL (no Firebase upload)
                            thumbnail_url = self.google_provider.get_photo_url(
                                photo_reference=first_photo,
                                max_width=800,
                                max_height=600
                            )
                            
                            if thumbnail_url:
                                logger.info(f"[THUMBNAIL] ✓ Set thumbnail URL for plan")
                            else:
                                logger.warning(f"[THUMBNAIL] Failed to get thumbnail URL")
                                
                        except Exception as e:
                            logger.warning(f"[THUMBNAIL] Error getting thumbnail URL: {e}")
                            # Continue without thumbnail - not critical for plan creation
            
            # Create Plan model
            plan = Plan(
                user_id=user_id,
                destination_place_id=request.destination_place_id,
                destination=request.destination_name or request.destination,
                destination_types=request.destination_types,
                destination_location=destination_location,
                thumbnail_url=thumbnail_url,
                num_days=request.num_days,
                start_date=request.start_date,
                origin=request.origin,
                preferences=request.preferences,
                title=request.title,
                status=PlanStatusEnum.PENDING
            )
            
            # Save to MongoDB
            created_plan = self.plan_repo.create(plan)
            
            logger.info(
                f"[INFO] Created plan {created_plan['plan_id']} for user {user_id}: "
                f"{request.num_days} days in {request.destination_name or request.destination}"
            )
            
            return created_plan
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to create plan: {e}")
            raise
    
    def generate_itinerary(self, plan_id: str) -> bool:
        """
        Generate itinerary using LangChain (synchronous).
        
        This method should be called by Celery worker (async).
        Tracks EXACT token usage and cost from API response.
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            True if generation succeeded
        """
        start_time = time.time()
        
        try:
            # Get plan
            plan = self.plan_repo.get_by_id(plan_id)
            if not plan:
                logger.error(f"[ERROR] Plan {plan_id} not found")
                return False
            
            user_id = plan.get('user_id')
            
            # Update status to PROCESSING
            self.plan_repo.update_status(plan_id, PlanStatusEnum.PROCESSING)
            logger.info(f"[INFO] Starting LangChain generation for plan {plan_id}")
            
            # --- STEP 1: Fetch POIs and Accommodations from repositories/providers ---
            poi_context, accommodation_context, poi_cache = self._fetch_pois_for_plan(plan, plan.get('num_days', 3))
            if poi_context:
                logger.info(f"[INFO] Using real POI data for plan {plan_id} ({len(poi_cache)} POIs cached)")
            else:
                logger.warning(f"[WARN] No POI data available for plan {plan_id}")
                poi_cache = {}  # Empty cache for post-processing
            
            if accommodation_context:
                logger.info(f"[INFO] Accommodation data available for plan {plan_id}")
            else:
                logger.warning(f"[WARN] No accommodation data available for plan {plan_id}")
                accommodation_context = "No accommodations found. Please suggest generic accommodation options."
            
            # --- STEP 2: Run LangChain ---
            chain = TravelPlannerChain()
            
            # TravelPlannerChain uses run() method with input_data dict
            result = chain.run(
                input_data={
                    'destination': plan.get('destination', 'Unknown'),
                    'num_days': plan.get('num_days', 3),
                    'preferences': plan.get('preferences', {}),
                    'start_date': plan.get('start_date')
                },
                poi_context=poi_context,
                accommodation_context=accommodation_context
            )
            
            if not result.get('success'):
                raise ValueError(result.get('error', 'LangChain generation failed'))
            
            # --- STEP 3: Post-process itinerary (featured_image, viewport) ---
            itinerary = result.get('itinerary', [])
            
            # Enrich itinerary with featured_image and viewport from POI cache
            if poi_cache:
                itinerary = self._post_process_itinerary(itinerary, poi_cache)
                logger.info(f"[INFO] Post-processed itinerary with featured_image and viewport")
            
            # --- STEP 4: Update plan with results ---
            
            # Use update_itinerary method (PlanRepository doesn't have generic update())
            self.plan_repo.update_itinerary(
                plan_id=plan_id,
                itinerary=itinerary,
                llm_model=result.get('model', 'unknown'),
                llm_response_raw=result.get('llm_response_raw'),
                metadata={
                    'generation_time_sec': time.time() - start_time,
                    'tokens_used': result.get('tokens_total', 0),
                    'cost_usd': result.get('cost_usd', 0),
                }
            )
            
            # Track cost (if cost service available)
            if user_id and self.cost_service:
                self.cost_service.track_api_call(
                    provider=result.get('provider', 'unknown'),
                    service='langchain',
                    endpoint='generate_itinerary',
                    tokens_input=result.get('tokens_input', 0),
                    tokens_output=result.get('tokens_output', 0),
                    cost_usd=result.get('cost_usd', 0),
                    success=result.get('success', False),
                    user_id=user_id,
                    plan_id=plan_id,
                    metadata={
                        'model': result.get('model'),
                        'num_days': plan.get('num_days'),
                        'destination': plan.get('destination')
                    }
                )
            
            logger.info(
                f"[SUCCESS] Generated itinerary for plan {plan_id} "
                f"in {time.time() - start_time:.2f}s"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to generate itinerary for {plan_id}: {e}")
            
            # Update plan status to FAILED
            try:
                self.plan_repo.update(plan_id, {
                    'status': PlanStatusEnum.FAILED.value,
                    'error_message': str(e),
                    'metadata': {
                        'generation_time_sec': time.time() - start_time,
                        'error': str(e)
                    }
                })
            except Exception:
                pass
            
            return False
    
    def get_plan(self, plan_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get plan by ID with optional ownership check.
        Enriches itinerary with POI locations for map display.
        
        Args:
            plan_id: Plan identifier
            user_id: User ID for ownership check (optional)
            
        Returns:
            Plan dict if found (and owned by user if user_id provided)
        """
        plan = self.plan_repo.get_by_id(plan_id)
        
        if plan and user_id and plan.get('user_id') != user_id:
            return None
        
        # Enrich itinerary with POI locations
        if plan and plan.get('itinerary'):
            plan = self._enrich_itinerary_with_poi_locations(plan)
        
        return plan
    
    def _enrich_itinerary_with_poi_locations(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich itinerary activities with POI location coordinates.
        
        Args:
            plan: Plan document with itinerary
            
        Returns:
            Plan with enriched itinerary containing POI locations
        """
        itinerary = plan.get('itinerary', [])
        if not itinerary:
            return plan
        
        # Collect all unique poi_ids from itinerary
        all_poi_ids = set()
        for day in itinerary:
            poi_ids = day.get('poi_ids', [])
            all_poi_ids.update(poi_ids)
        
        if not all_poi_ids:
            return plan
        
        # Fetch all POIs in one query
        try:
            poi_map = self.poi_repo.get_by_ids(list(all_poi_ids))
            logger.debug(f"[ENRICH] Fetched {len(poi_map)}/{len(all_poi_ids)} POIs for plan {plan.get('plan_id')}")
        except Exception as e:
            logger.warning(f"[ENRICH] Failed to fetch POI locations: {e}")
            return plan
        
        # Enrich each day's activities with POI data
        enriched_itinerary = []
        for day in itinerary:
            enriched_day = dict(day)  # Copy to avoid mutating original
            poi_ids = day.get('poi_ids', [])
            activities = day.get('activities', [])
            
            # Create enriched activities list with POI details
            enriched_activities = []
            for i, poi_id in enumerate(poi_ids):
                poi = poi_map.get(poi_id)
                
                # Get activity text (if available)
                activity_text = activities[i] if i < len(activities) else None
                
                if poi:
                    # Extract location from GeoJSON format
                    location = poi.get('location', {})
                    coords = location.get('coordinates', [])
                    
                    enriched_activity = {
                        'poi_id': poi_id,
                        'poi_name': poi.get('name') or poi.get('name_en'),
                        'activity': activity_text,
                        'location': {
                            'latitude': coords[1] if len(coords) >= 2 else None,
                            'longitude': coords[0] if len(coords) >= 2 else None,
                        } if coords else None,
                        'address': poi.get('address', {}).get('formatted') or poi.get('address', {}).get('full'),
                        'category': poi.get('category'),
                        'rating': poi.get('ratings', {}).get('average'),
                        'thumbnail_url': poi.get('thumbnail_url') or (
                            poi.get('photos', [{}])[0].get('url') if poi.get('photos') else None
                        ),
                    }
                else:
                    # POI not found in DB, use minimal info
                    enriched_activity = {
                        'poi_id': poi_id,
                        'poi_name': poi_id.replace('poi_', '').replace('_', ' ').title(),
                        'activity': activity_text,
                        'location': None,
                    }
                
                enriched_activities.append(enriched_activity)
            
            enriched_day['activities'] = enriched_activities
            enriched_itinerary.append(enriched_day)
        
        plan['itinerary'] = enriched_itinerary
        return plan
    
    def regenerate_plan(self, plan_id: str, user_id: str, request: PlanUpdateRequest) -> bool:
        """
        Regenerate plan with new preferences (reset to PENDING status).
        
        Args:
            plan_id: Plan identifier
            user_id: User ID for ownership check
            request: Update data with new preferences
            
        Returns:
            True if update succeeded
        """
        # Check ownership
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan or plan.get('user_id') != user_id:
            return False
        
        # Build update dict
        update_data = {
            'status': PlanStatusEnum.PENDING.value,
            'itinerary': [],  # Clear old itinerary
            'version': plan.get('version', 1) + 1,  # Increment version
        }
        
        if request.title:
            update_data['title'] = request.title
        if request.preferences:
            update_data['preferences'] = request.preferences
        if request.start_date:
            update_data['start_date'] = request.start_date
        if request.origin:
            update_data['origin'] = request.origin.model_dump() if hasattr(request.origin, 'model_dump') else request.origin
        
        result = self.plan_repo.update(plan_id, update_data)
        return result is not None
    
    def list_plans(
        self, 
        user_id: str, 
        page: int = 1, 
        limit: int = 20, 
        status: Optional[PlanStatusEnum] = None
    ) -> Dict[str, Any]:
        """
        List user's plans with pagination.
        
        Args:
            user_id: User identifier
            page: Page number (1-based)
            limit: Items per page
            status: Filter by status
            
        Returns:
            {plans: [...], total: int, page: int, limit: int, total_pages: int}
        """
        skip = (page - 1) * limit
        plans = self.plan_repo.get_by_user(user_id, skip, limit, status)
        total = self.plan_repo.count_by_user(user_id, status)
        
        return {
            'plans': plans,
            'total': total,
            'page': page,
            'limit': limit
        }
    
    def get_user_plans(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        status: Optional[PlanStatusEnum] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user's plans (legacy method for backward compatibility).
        
        Args:
            user_id: User identifier
            skip: Offset for pagination
            limit: Max results per page
            status: Filter by status
            
        Returns:
            List of plan documents
        """
        return self.plan_repo.get_by_user(user_id, skip, limit, status)
    
    def count_user_plans(self, user_id: str, status: Optional[PlanStatusEnum] = None) -> int:
        """
        Count user's plans (legacy method for backward compatibility).
        
        Args:
            user_id: User identifier
            status: Filter by status
            
        Returns:
            Total plan count
        """
        return self.plan_repo.count_by_user(user_id, status)
    
    def delete_plan(self, plan_id: str, user_id: str) -> bool:
        """
        Soft delete plan (move to trash) with ownership check.
        
        Args:
            plan_id: Plan identifier
            user_id: User ID for ownership check
            
        Returns:
            True if moved to trash successfully
        """
        # Check ownership
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan or plan.get('user_id') != user_id:
            return False
        
        return self.plan_repo.delete(plan_id)
    
    def restore_plan(self, plan_id: str, user_id: str) -> bool:
        """
        Restore plan from trash with ownership check.
        
        Args:
            plan_id: Plan identifier
            user_id: User ID for ownership check
            
        Returns:
            True if restored successfully
        """
        # Check ownership
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan or plan.get('user_id') != user_id:
            return False
        
        return self.plan_repo.restore_from_trash(plan_id)
    
    def permanent_delete_plan(self, plan_id: str, user_id: str) -> bool:
        """
        Permanently delete plan with ownership check.
        
        Args:
            plan_id: Plan identifier
            user_id: User ID for ownership check
            
        Returns:
            True if permanently deleted successfully
        """
        # Check ownership and ensure it's in trash
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan or plan.get('user_id') != user_id:
            return False
        
        if not plan.get('is_deleted'):
            logger.warning(f"[WARN] Attempt to permanently delete non-trashed plan {plan_id}")
            return False
        
        return self.plan_repo.permanent_delete(plan_id)
    
    def get_trash_plans(self, user_id: str, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """
        Get user's deleted plans (trash) with pagination.
        
        Args:
            user_id: User identifier
            page: Page number (1-based)
            limit: Items per page
            
        Returns:
            {plans: [...], total: int, page: int, limit: int}
        """
        skip = (page - 1) * limit
        plans = self.plan_repo.get_trash_plans(user_id, skip, limit)
        total = self.plan_repo.count_trash_plans(user_id)
        
        return {
            'plans': plans,
            'total': total,
            'page': page,
            'limit': limit
        }
    
    def toggle_plan_sharing(self, plan_id: str, user_id: str, is_public: bool) -> Optional[Dict[str, Any]]:
        """
        Toggle plan public sharing status.
        
        Args:
            plan_id: Plan identifier
            user_id: User ID for ownership check
            is_public: Public visibility flag
            
        Returns:
            Updated plan with share_token if successful
        """
        # Check ownership
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan or plan.get('user_id') != user_id:
            return None
        
        # Generate share token if making public
        share_token = None
        if is_public:
            import secrets
            share_token = secrets.token_urlsafe(16)
        
        # Update sharing settings
        success = self.plan_repo.update_sharing(plan_id, is_public, share_token)
        
        if success:
            # Return updated plan
            updated_plan = self.plan_repo.get_by_id(plan_id)
            return updated_plan
        
        return None
    
    def get_public_plan(self, share_token: str) -> Optional[Dict[str, Any]]:
        """
        Get public plan by share token (no auth required).
        
        Args:
            share_token: Share token from URL
            
        Returns:
            Plan dict if found and public
        """
        plan = self.plan_repo.get_by_share_token(share_token)

        # Enrich itinerary with POI locations for map display (match private detail response)
        if plan and plan.get('itinerary'):
            plan = self._enrich_itinerary_with_poi_locations(plan)

        return plan
    
    def update_plan(
        self, 
        plan_id: str, 
        user_id: str, 
        request: PlanUpdateRequest
    ) -> Optional[Dict[str, Any]]:
        """
        Update plan with ownership check.
        
        Args:
            plan_id: Plan identifier
            user_id: User ID for ownership check
            request: Update data
            
        Returns:
            Updated plan dict if successful
        """
        # Check ownership
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan or plan.get('user_id') != user_id:
            return None
        
        # Build update dict
        update_data = {}
        if request.title:
            update_data['title'] = request.title
        if request.preferences:
            update_data['preferences'] = request.preferences
        if request.start_date:
            update_data['start_date'] = request.start_date
        if request.origin:
            update_data['origin'] = request.origin.model_dump() if hasattr(request.origin, 'model_dump') else request.origin
        
        if update_data:
            return self.plan_repo.update(plan_id, update_data)
        
        return plan

    def patch_plan(
        self, 
        plan_id: str, 
        user_id: str, 
        request: PlanPatchRequest
    ) -> Optional[Dict[str, Any]]:
        """
        Partial update for non-core plan fields.
        Does NOT trigger regeneration or reset status.
        
        Editable fields:
        - Plan level: title, thumbnail_url, start_date, estimated_total_cost
        - Day level: notes, activities, estimated_times, estimated_cost_vnd, accommodation fields
        
        Args:
            plan_id: Plan identifier
            user_id: User ID for ownership check
            request: PlanPatchRequest with partial updates
            
        Returns:
            Updated plan dict if successful, None if not found/unauthorized
        """
        # Step 1: Ownership check
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan or plan.get('user_id') != user_id:
            logger.warning(f"[PATCH] Plan {plan_id} not found or user {user_id} not authorized")
            return None
        
        update_data = {}
        
        # Step 2: Plan-level field updates
        if request.title is not None:
            update_data['title'] = request.title
            logger.info(f"[PATCH] Updating title to: {request.title}")
            
        if request.thumbnail_url is not None:
            update_data['thumbnail_url'] = request.thumbnail_url
            
        if request.estimated_total_cost is not None:
            update_data['estimated_total_cost'] = request.estimated_total_cost
            
        if request.start_date is not None:
            update_data['start_date'] = request.start_date
            # Auto-calculate end_date based on num_days
            try:
                from datetime import datetime, timedelta
                start = datetime.strptime(request.start_date, '%Y-%m-%d')
                num_days = plan.get('num_days', 1)
                end = start + timedelta(days=num_days - 1)
                update_data['end_date'] = end.strftime('%Y-%m-%d')
                
                # Also update date field in each day of itinerary
                itinerary = plan.get('itinerary', [])
                if itinerary:
                    for i, day_plan in enumerate(itinerary):
                        day_date = start + timedelta(days=i)
                        day_plan['date'] = day_date.strftime('%Y-%m-%d')
                    update_data['itinerary'] = itinerary
                    
                logger.info(f"[PATCH] Updated start_date to {request.start_date}, end_date to {update_data['end_date']}")
            except ValueError as e:
                logger.warning(f"[PATCH] Invalid date format: {e}")
        
        # Step 3: Itinerary day-level updates
        if request.itinerary_updates:
            itinerary = plan.get('itinerary', [])
            num_days = plan.get('num_days', 0)
            
            for day_patch in request.itinerary_updates:
                day_idx = day_patch.day - 1  # Convert to 0-based index
                
                # Validate day bounds
                if day_idx < 0 or day_idx >= len(itinerary):
                    logger.warning(f"[PATCH] Day {day_patch.day} out of bounds (1-{num_days}), skipping")
                    continue
                
                # Apply updates to the day
                day_data = itinerary[day_idx]
                
                # Editable fields
                if day_patch.notes is not None:
                    day_data['notes'] = day_patch.notes
                    
                if day_patch.activities is not None:
                    day_data['activities'] = day_patch.activities
                    
                if day_patch.estimated_times is not None:
                    day_data['estimated_times'] = day_patch.estimated_times
                    
                if day_patch.estimated_cost_vnd is not None:
                    day_data['estimated_cost_vnd'] = day_patch.estimated_cost_vnd
                    
                # Accommodation fields
                if day_patch.accommodation_name is not None:
                    day_data['accommodation_name'] = day_patch.accommodation_name
                    
                if day_patch.accommodation_address is not None:
                    day_data['accommodation_address'] = day_patch.accommodation_address
                    
                if day_patch.check_in_time is not None:
                    day_data['check_in_time'] = day_patch.check_in_time
                    
                if day_patch.check_out_time is not None:
                    day_data['check_out_time'] = day_patch.check_out_time
                
                logger.info(f"[PATCH] Updated day {day_patch.day} with {len([f for f in [day_patch.notes, day_patch.activities, day_patch.estimated_times, day_patch.estimated_cost_vnd, day_patch.accommodation_name, day_patch.accommodation_address, day_patch.check_in_time, day_patch.check_out_time] if f is not None])} fields")
            
            update_data['itinerary'] = itinerary
        
        # Step 4: Apply updates if any
        if update_data:
            updated_plan = self.plan_repo.update(plan_id, update_data)
            
            # Enrich with POI locations for map display
            if updated_plan and updated_plan.get('itinerary'):
                updated_plan = self._enrich_itinerary_with_poi_locations(updated_plan)
            
            return updated_plan
        
        # No updates, return current plan (enriched)
        if plan.get('itinerary'):
            plan = self._enrich_itinerary_with_poi_locations(plan)
        return plan
