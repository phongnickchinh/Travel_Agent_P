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
from ..model.mongo.poi import POI, POISearchRequest
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
            cost_usage_service: Cost tracking service
        """
        self.plan_repo = plan_repository or PlanRepository()
        self.poi_repo = poi_repository or POIRepository()
        self.place_detail_repo = place_detail_repository or PlaceDetailRepository()
        self.google_provider = google_places_provider or GooglePlacesProvider()
        self.cost_service = cost_usage_service or CostUsageService()
        
        logger.info("[INFO] PlannerService initialized with clean architecture (no service imports)")
    
    # ============================================
    # DESTINATION RESOLUTION
    # ============================================
    
    def _resolve_destination(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Resolve destination place_id to full details with location.
        
        Strategy:
        1. Check PlaceDetailRepository (MongoDB cache)
        2. If miss, call Google Places API
        3. Cache result in PlaceDetailRepository
        
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
        
        # Step 2: Fetch from Google Places API
        logger.info(f"[CACHE MISS] Fetching destination from Google API: {place_id}")
        try:
            google_data = self.google_provider.get_details(place_id)
            
            if not google_data:
                logger.warning(f"[RESOLVE] Google API returned no data for {place_id}")
                return None
            
            # Step 3: Cache to MongoDB
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
                location = {
                    'latitude': resolved.get('geometry', {}).get('location', {}).get('latitude'),
                    'longitude': resolved.get('geometry', {}).get('location', {}).get('longitude')
                }
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
        if not interests:
            interests = ['tourist_attraction', 'restaurant', 'hotel']
        
        # Search by each interest type (Google API only accepts 1 type per request)
        for interest in interests[:5]:  # Limit to 5 types to control API costs
            try:
                # Use nearby_search for geo-based results
                pois = self.google_provider.nearby_search(
                    location=location,
                    radius=15000,  # 15km
                    types=[interest],
                    max_results=min(limit // len(interests) + 1, 20)
                )
                
                results.extend(pois)
                
                if len(results) >= limit:
                    break
                    
            except Exception as e:
                logger.warning(f"[Google] Search for '{interest}' failed: {e}")
                continue
        
        return results[:limit]
    
    def _cache_poi_to_mongodb(self, poi_data: Dict[str, Any]) -> bool:
        """
        Cache POI data to MongoDB.
        
        Args:
            poi_data: POI dict from Google API
            
        Returns:
            True if cached successfully
        """
        try:
            # Check if already exists
            place_id = poi_data.get('provider', {}).get('id') or poi_data.get('place_id')
            if place_id:
                existing = self.poi_repo.get_by_id(f"poi_{place_id}")
                if existing:
                    return True  # Already cached
            
            # Create POI model and save
            poi = POI.from_provider_data(poi_data)
            self.poi_repo.create(poi)
            return True
            
        except Exception as e:
            logger.warning(f"[CACHE] Failed to cache POI: {e}")
            return False
    
    def _format_pois_for_prompt(self, pois: List[Dict[str, Any]], max_pois: int = 30) -> str:
        """
        Format POI list for LLM prompt.
        
        Args:
            pois: List of POI dicts
            max_pois: Maximum POIs to include
            
        Returns:
            Formatted string for LLM context
        """
        if not pois:
            return ""
        
        lines = []
        lines.append("=== AVAILABLE PLACES OF INTEREST ===\n")
        
        for i, poi in enumerate(pois[:max_pois], 1):
            name = poi.get('name', 'Unknown')
            categories = poi.get('categories', [])
            rating = poi.get('ratings', {}).get('average', 'N/A')
            description = poi.get('description', {}).get('short', '')
            poi_id = poi.get('poi_id', f'poi_{i}')
            
            line = f"{i}. [{poi_id}] {name}"
            
            if categories:
                line += f" ({', '.join(categories[:2])})"
            
            if rating and rating != 'N/A':
                line += f" ★{rating}"
            
            if description:
                line += f"\n   {description[:100]}..."
            
            lines.append(line)
        
        lines.append(f"\nTotal: {len(pois[:max_pois])} places available")
        
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
            # Resolve destination to get location
            destination_location = None
            if request.destination_place_id:
                resolved = self._resolve_destination(request.destination_place_id)
                if resolved:
                    geometry = resolved.get('geometry', {})
                    location_data = geometry.get('location', {})
                    destination_location = {
                        'latitude': location_data.get('latitude'),
                        'longitude': location_data.get('longitude')
                    }
            
            # Create Plan model
            plan = Plan(
                user_id=user_id,
                destination_place_id=request.destination_place_id,
                destination=request.destination_name or request.destination,
                destination_types=request.destination_types,
                destination_location=destination_location,
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
            
            result = chain.generate_itinerary(
                destination=plan.get('destination', 'Unknown'),
                num_days=plan.get('num_days', 3),
                preferences=plan.get('preferences', {}),
                poi_context=poi_context
            )
            
            if not result.get('success'):
                raise ValueError(result.get('error', 'LangChain generation failed'))
            
            # --- STEP 3: Update plan with results ---
            itinerary = result.get('itinerary', [])
            
            self.plan_repo.update(plan_id, {
                'status': PlanStatusEnum.COMPLETED.value,
                'itinerary': itinerary,
                'llm_model': result.get('model'),
                'llm_response_raw': result.get('raw_response'),
                'total_pois': sum(len(day.get('poi_ids', [])) for day in itinerary),
                'metadata': {
                    'generation_time_sec': time.time() - start_time,
                    'tokens_used': result.get('tokens_used', 0),
                    'cost_usd': result.get('cost_usd', 0),
                }
            })
            
            # Track cost
            if user_id:
                self.cost_service.track_usage(
                    user_id=user_id,
                    operation='plan_generation',
                    tokens=result.get('tokens_used', 0),
                    cost_usd=result.get('cost_usd', 0),
                    model=result.get('model')
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
    
    def get_plan(self, plan_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get plan by ID with ownership check.
        
        Args:
            plan_id: Plan identifier
            user_id: User ID for ownership check
            
        Returns:
            Plan dict if found and owned by user
        """
        plan = self.plan_repo.get_by_id(plan_id)
        
        if plan and plan.get('user_id') == user_id:
            return plan
        
        return None
    
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
        return self.plan_repo.list_by_user(
            user_id=user_id,
            page=page,
            limit=limit,
            status=status
        )
    
    def delete_plan(self, plan_id: str, user_id: str) -> bool:
        """
        Delete plan with ownership check.
        
        Args:
            plan_id: Plan identifier
            user_id: User ID for ownership check
            
        Returns:
            True if deleted
        """
        # Check ownership
        plan = self.plan_repo.get_by_id(plan_id)
        if not plan or plan.get('user_id') != user_id:
            return False
        
        return self.plan_repo.delete(plan_id)
    
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
