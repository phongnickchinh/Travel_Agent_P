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

from ..model.mongo.plan import Plan, PlanStatusEnum, PlanCreateRequest, PlanUpdateRequest
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
    
    def _fetch_pois_for_plan(self, plan: Dict[str, Any]) -> Optional[str]:
        """
        Fetch POIs for a plan and format for LLM prompt.
        
        Strategy:
        1. Get destination location from plan
        2. Search nearby POIs in MongoDB (POIRepository)
        3. If < TARGET_POI_COUNT, fetch more from Google API
        4. Cache new POIs to MongoDB
        5. Format for LLM prompt
        
        Args:
            plan: Plan document from MongoDB
            
        Returns:
            Formatted POI context string for LLM prompt
        """
        destination_place_id = plan.get('destination_place_id')
        destination_location = plan.get('destination_location')
        destination_name = plan.get('destination', 'Unknown')
        preferences = plan.get('preferences', {}) or {}
        interests = preferences.get('interests', [])
        
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
            mongo_pois = self._search_pois_mongodb(location, interests)
            all_pois.extend(mongo_pois)
            logger.info(f"[MongoDB] Found {len(mongo_pois)} cached POIs")
        except Exception as e:
            logger.warning(f"[MongoDB] POI search failed: {e}")
        
        # Step 2: If not enough, fetch from Google
        if len(all_pois) < TARGET_POI_COUNT:
            needed = TARGET_POI_COUNT - len(all_pois)
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
                return None
        
        # Format for LLM prompt
        poi_context = self._format_pois_for_prompt(all_pois[:TARGET_POI_COUNT])
        logger.info(f"[POI_FETCH] Formatted {len(all_pois)} POIs for prompt")
        
        return poi_context
    
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
        Format POI list for LLM prompt with coordinates for geographic optimization.
        
        Args:
            pois: List of POI dicts
            max_pois: Maximum POIs to include
            
        Returns:
            Formatted string for LLM context including coordinates
        """
        if not pois:
            return ""
        
        lines = []
        lines.append("=== AVAILABLE PLACES OF INTEREST (with coordinates) ===\n")
        lines.append("NOTE: Use coordinates to group nearby POIs together for optimal travel route.\n")
        
        for i, poi in enumerate(pois[:max_pois], 1):
            name = poi.get('name', 'Unknown')
            categories = poi.get('categories', [])
            rating = poi.get('ratings', {}).get('average', 'N/A')
            description = poi.get('description', {}).get('short', '')
            poi_id = poi.get('poi_id', f'poi_{i}')
            
            # Extract coordinates [lng, lat] from GeoJSON format
            location = poi.get('location', {})
            coords = location.get('coordinates', [None, None])
            lat = coords[1] if len(coords) > 1 else None
            lng = coords[0] if len(coords) > 0 else None
            
            line = f"{i}. [{poi_id}] {name}"
            
            # Add coordinates for geographic grouping
            if lat and lng:
                line += f" @({lat:.5f}, {lng:.5f})"
            
            if categories:
                line += f" ({', '.join(categories[:2])})"
            
            if rating and rating != 'N/A':
                line += f" ★{rating}"
            
            if description:
                line += f"\n   {description[:100]}..."
            
            lines.append(line)
        
        lines.append(f"\nTotal: {len(pois[:max_pois])} places available")
        lines.append("\nIMPORTANT: Group POIs with similar coordinates together in the same day to minimize travel distance.")
        
        return "\n".join(lines)
    
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
            
            # --- STEP 1: Fetch POIs from repositories/providers ---
            poi_context = self._fetch_pois_for_plan(plan)
            if poi_context:
                logger.info(f"[INFO] Using real POI data for plan {plan_id}")
            else:
                logger.warning(f"[WARN] No POI data available for plan {plan_id}")
            
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
                poi_context=poi_context
            )
            
            if not result.get('success'):
                raise ValueError(result.get('error', 'LangChain generation failed'))
            
            # --- STEP 3: Update plan with results ---
            itinerary = result.get('itinerary', [])
            
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
        return self.plan_repo.get_by_share_token(share_token)
    
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
