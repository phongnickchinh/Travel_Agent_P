"""
Places Controller - API Endpoints for POI Operations
======================================================

Purpose:
- RESTful API for POI search and retrieval
- Write-through cache integration (Provider → MongoDB → ES)
- Request validation and error handling
- Standardized response format

Author: Travel Agent P Team
Date: November 27, 2025
"""

from flask import request, jsonify
from typing import Optional
import logging

from . import places_bp
from ...service.places_service import PlacesService
from ...utils.response_helpers import build_error_response, build_success_response
from ...core.di_container import DIContainer
from ...middleware import admin_required

logger = logging.getLogger(__name__)


class PlacesController:
    """
    Places Controller - ADMIN & TESTING ONLY
    
    ⚠️ WARNING: These endpoints are for debugging and testing purposes.
    Regular users should NOT access these directly.
    User-facing features should use ItineraryController instead.
    
    🔒 ALL ENDPOINTS REQUIRE ADMIN ROLE
    
    Endpoints:
    - GET /api/places/search - Search POIs (admin only)
    - GET /api/places/{poi_id} - Get POI details (admin only)
    - POST /api/places/refresh - Refresh stale POIs (admin only)
    - POST /api/places/import - Bulk import POIs (admin only)
    
    Example Requests:
        # Login as admin first
        POST /api/admin/auth/login
        Body: {"username": "admin", "password": "..."}
        
        # Use admin token
        GET /api/places/search?q=restaurant&lat=16.0544&lng=108.2428
        Headers: Authorization: Bearer {admin_token}
    """
    
    def __init__(self, places_service: PlacesService):
        """Initialize controller with service dependency."""
        self.places_service = places_service
        self._register_routes()
        logger.info("[INFO] PlacesController initialized")
    
    def _register_routes(self):
        """Register all routes with Flask Blueprint (admin-only)."""
        # 🔒 All endpoints protected by @admin_required
        places_bp.add_url_rule("/search", "search", admin_required(self.search_places), methods=["GET"])
        places_bp.add_url_rule("/<poi_id>", "get_by_id", admin_required(self.get_place_by_id), methods=["GET"])
        places_bp.add_url_rule("/refresh", "refresh", admin_required(self.refresh_stale_pois), methods=["POST"])
        places_bp.add_url_rule("/import", "bulk_import", admin_required(self.bulk_import_pois), methods=["POST"])
    
    def search_places(self):
        """
        Search POIs with write-through cache strategy.
        
        Query Parameters:
            q (required): Search query (e.g., "restaurants", "beach")
            lat (required): Latitude (-90 to 90)
            lng (required): Longitude (-180 to 180)
            radius (optional): Search radius in km (default: 5, max: 50)
            min_results (optional): Min results for cache hit (default: 5)
            force_refresh (optional): Force API call, skip cache (default: false)
            types (optional): Comma-separated POI types (e.g., "restaurant,cafe")
            min_rating (optional): Minimum rating (0-5)
            price_level (optional): Price level filter
            max_results (optional): Max results to return (default: 20, max: 100)
        
        Response Success (200):
            {
                "resultMessage": {"en": "...", "vn": "..."},
                "resultCode": "PLACES_SEARCH_SUCCESS",
                "results": [POI objects],
                "total": 15,
                "source": "cache|provider|hybrid",
                "cached_count": 10,
                "new_count": 5,
                "cost_saved": true
            }
        
        Response Error (400):
            {
                "resultMessage": {"en": "...", "vn": "..."},
                "resultCode": "INVALID_PARAMETERS"
            }
        
        Examples:
            # Search restaurants near Đà Nẵng
            GET /places/search?q=restaurant&lat=16.0544&lng=108.2428&radius=5
            
            # Search beaches with filters
            GET /places/search?q=beach&lat=16.0544&lng=108.2428&radius=10&min_rating=4.0&types=beach
            
            # Force refresh from API
            GET /places/search?q=cafe&lat=16.0544&lng=108.2428&force_refresh=true
        """
        try:
            query = request.args.get('q', '').strip()
            lat = request.args.get('lat', type=float)
            lng = request.args.get('lng', type=float)
            radius = request.args.get('radius', default=5.0, type=float)
            min_results = request.args.get('min_results', default=5, type=int)
            force_refresh = request.args.get('force_refresh', default='false').lower() == 'true'
            types = request.args.get('types', '').strip()
            min_rating = request.args.get('min_rating', type=float)
            price_level = request.args.get('price_level', '').strip()
            max_results = request.args.get('max_results', default=20, type=int)
            
            # Validate required parameters
            if not query:
                return build_error_response(
                    "Query parameter 'q' is required",
                    "Tham số 'q' là bắt buộc",
                    "MISSING_QUERY",
                    400
                )
            
            if lat is None or lng is None:
                return build_error_response(
                    "Latitude and longitude are required",
                    "Vĩ độ và kinh độ là bắt buộc",
                    "MISSING_LOCATION",
                    400
                )
            
            # Validate parameter ranges
            if not (-90 <= lat <= 90):
                return build_error_response(
                    "Latitude must be between -90 and 90",
                    "Vĩ độ phải nằm trong khoảng -90 đến 90",
                    "INVALID_LATITUDE",
                    400
                )
            
            if not (-180 <= lng <= 180):
                return build_error_response(
                    "Longitude must be between -180 and 180",
                    "Kinh độ phải nằm trong khoảng -180 đến 180",
                    "INVALID_LONGITUDE",
                    400
                )
            
            if not (0.1 <= radius <= 50):
                return build_error_response(
                    "Radius must be between 0.1 and 50 km",
                    "Bán kính phải từ 0.1 đến 50 km",
                    "INVALID_RADIUS",
                    400
                )
            
            if not (1 <= max_results <= 100):
                return build_error_response(
                    "Max results must be between 1 and 100",
                    "Số kết quả tối đa phải từ 1 đến 100",
                    "INVALID_MAX_RESULTS",
                    400
                )
            
            if min_rating is not None and not (0 <= min_rating <= 5):
                return build_error_response(
                    "Minimum rating must be between 0 and 5",
                    "Đánh giá tối thiểu phải từ 0 đến 5",
                    "INVALID_MIN_RATING",
                    400
                )
            location = {
                "latitude": lat,
                "longitude": lng
            }
            kwargs = {"max_results": max_results}
            
            if types:
                kwargs["types"] = [t.strip() for t in types.split(',')]
            
            if min_rating is not None:
                kwargs["min_rating"] = min_rating
            
            if price_level:
                kwargs["price_level"] = price_level
            
            # Call service
            logger.info(f"[SEARCH] Places search: q='{query}', location={location}, radius={radius}km")
            
            result = self.places_service.search_and_cache(
                query=query,
                location=location,
                radius_km=radius,
                min_results=min_results,
                force_refresh=force_refresh,
                **kwargs
            )
            return build_success_response(
                f"Found {result['total']} places",
                f"Tìm thấy {result['total']} địa điểm",
                "PLACES_SEARCH_SUCCESS",
                data=result,
                status_code=200
            )
        
        except ValueError as e:
            logger.error(f"[ERROR] Validation error: {e}")
            return build_error_response(
                f"Invalid parameter: {str(e)}",
                f"Tham số không hợp lệ: {str(e)}",
                "INVALID_PARAMETERS",
                400
            )
        
        except Exception as e:
            logger.error(f"[ERROR] Search failed: {e}", exc_info=True)
            return build_error_response(
                "An error occurred while searching places",
                "Đã xảy ra lỗi khi tìm kiếm địa điểm",
                "SEARCH_ERROR",
                500
            )
    
    def get_place_by_id(self, poi_id: str):
        """
        Get POI details by ID.
        
        Path Parameters:
            poi_id: POI identifier (e.g., "poi_mykhebeach_wecq6uk")
        
        Query Parameters:
            include_fresh (optional): If true and not cached, try provider API (default: false)
        
        Response Success (200):
            {
                "resultMessage": {"en": "...", "vn": "..."},
                "resultCode": "PLACE_FOUND",
                "poi": {POI object}
            }
        
        Response Error (404):
            {
                "resultMessage": {"en": "...", "vn": "..."},
                "resultCode": "PLACE_NOT_FOUND"
            }
        
        Examples:
            # Get cached POI
            GET /api/places/poi_mykhebeach_wecq6uk
            
            # Get with fresh data fallback
            GET /api/places/poi_hoian_old_town?include_fresh=true
        """
        try:
            # Validate poi_id
            if not poi_id or not poi_id.strip():
                return build_error_response(
                    "POI ID is required",
                    "ID địa điểm là bắt buộc",
                    "MISSING_POI_ID",
                    400
                )
            
            include_fresh = request.args.get('include_fresh', default='false').lower() == 'true'
            
            logger.info(f"[SEARCH] Get POI: {poi_id} (include_fresh={include_fresh})")
            
            # Call service
            poi = self.places_service.get_by_id(poi_id, include_fresh=include_fresh)
            
            if not poi:
                return build_error_response(
                    f"Place with ID '{poi_id}' not found",
                    f"Không tìm thấy địa điểm có ID '{poi_id}'",
                    "PLACE_NOT_FOUND",
                    404
                )
            return build_success_response(
                "Place found",
                "Đã tìm thấy địa điểm",
                "PLACE_FOUND",
                data={"poi": poi},
                status_code=200
            )
        
        except Exception as e:
            logger.error(f"[ERROR] Get by ID failed: {e}", exc_info=True)
            return build_error_response(
                "An error occurred while retrieving the place",
                "Đã xảy ra lỗi khi lấy thông tin địa điểm",
                "GET_PLACE_ERROR",
                500
            )
    
    def refresh_stale_pois(self):
        """
        Trigger background refresh of stale POIs (Admin only).
        
        Request Body:
            {
                "limit": 100  // Max POIs to refresh (default: 100, max: 500)
            }
        
        Response Success (200):
            {
                "resultMessage": {"en": "...", "vn": "..."},
                "resultCode": "REFRESH_SUCCESS",
                "processed": 100,
                "updated": 85,
                "failed": 15,
                "errors": [...]
            }
        
        Example:
            POST /api/places/refresh
            Body: {"limit": 50}
        """
        try:
            # if not is_admin(request):
            
            data = request.get_json() or {}
            limit = data.get('limit', 100)
            
            # Validate limit
            if not (1 <= limit <= 500):
                return build_error_response(
                    "Limit must be between 1 and 500",
                    "Giới hạn phải từ 1 đến 500",
                    "INVALID_LIMIT",
                    400
                )
            
            logger.info(f"[REFRESH] Refresh stale POIs: limit={limit}")
            
            # Call service
            stats = self.places_service.refresh_stale_pois(limit=limit)
            return build_success_response(
                f"Refreshed {stats['updated']} out of {stats['processed']} POIs",
                f"Đã làm mới {stats['updated']} trong số {stats['processed']} địa điểm",
                "REFRESH_SUCCESS",
                data=stats,
                status_code=200
            )
        
        except Exception as e:
            logger.error(f"[ERROR] Refresh failed: {e}", exc_info=True)
            return build_error_response(
                "An error occurred while refreshing POIs",
                "Đã xảy ra lỗi khi làm mới địa điểm",
                "REFRESH_ERROR",
                500
            )
    
    def bulk_import_pois(self):
        """
        Bulk import POIs (Admin only).
        
        Use case: Seeding, migration, data import
        
        Request Body:
            {
                "pois": [POI objects],
                "skip_duplicates": true
            }
        
        Response Success (200):
            {
                "resultMessage": {"en": "...", "vn": "..."},
                "resultCode": "IMPORT_SUCCESS",
                "total": 100,
                "inserted": 85,
                "updated": 10,
                "skipped": 5,
                "errors": 0
            }
        
        Example:
            POST /api/places/import
            Body: {
                "pois": [...],
                "skip_duplicates": true
            }
        """
        try:
            # if not is_admin(request):
            
            data = request.get_json()
            
            if not data or 'pois' not in data:
                return build_error_response(
                    "POIs array is required",
                    "Mảng POIs là bắt buộc",
                    "MISSING_POIS",
                    400
                )
            
            pois = data['pois']
            skip_duplicates = data.get('skip_duplicates', True)
            
            if not isinstance(pois, list):
                return build_error_response(
                    "POIs must be an array",
                    "POIs phải là một mảng",
                    "INVALID_POIS_FORMAT",
                    400
                )
            
            if len(pois) > 1000:
                return build_error_response(
                    "Cannot import more than 1000 POIs at once",
                    "Không thể import hơn 1000 POIs cùng lúc",
                    "TOO_MANY_POIS",
                    400
                )
            
            logger.info(f"[IMPORT] Bulk import: {len(pois)} POIs")
            
            # Call service
            stats = self.places_service.bulk_import(pois, skip_duplicates=skip_duplicates)
            return build_success_response(
                f"Imported {stats['inserted']} POIs ({stats['updated']} updated, {stats['skipped']} skipped)",
                f"Đã import {stats['inserted']} POIs ({stats['updated']} cập nhật, {stats['skipped']} bỏ qua)",
                "IMPORT_SUCCESS",
                data=stats,
                status_code=200
            )
        
        except Exception as e:
            logger.error(f"[ERROR] Bulk import failed: {e}", exc_info=True)
            return build_error_response(
                "An error occurred while importing POIs",
                "Đã xảy ra lỗi khi import POIs",
                "IMPORT_ERROR",
                500
            )


# Initialize controller with DI
def init_places_controller():
    """Initialize Places controller with dependency injection."""
    container = DIContainer.get_instance()
    places_service = container.resolve('PlacesService')
    return PlacesController(places_service)
