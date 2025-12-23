"""
Search Controller - Elasticsearch Search API Endpoints
=======================================================

Purpose:
- High-performance search API powered by Elasticsearch
- Autocomplete with edge n-gram (5-15ms latency)
- Geo-distance search with filters
- Full-text search with relevance scoring
- Graceful fallback to MongoDB

Author: Travel Agent P Team
Date: November 27, 2025
"""

from flask import request, jsonify
from typing import Optional, List
import logging

from . import search_bp
from app.service.search_service import SearchService
from app.utils.response_helpers import build_error_response, build_success_response
from app.core.di_container import DIContainer

logger = logging.getLogger(__name__)


class SearchController:
    """
    Search Controller - Elasticsearch-powered Search API
    
    Endpoints:
    - GET /api/search - Full-text + geo + filter search
    - GET /api/search/nearby - Get nearby POIs
    - GET /api/search/type/{type} - Browse by category
    - GET /api/search/popular - Get popular POIs
    
    NOTE: Autocomplete moved to /v2/autocomplete (autocomplete_controller.py)
    
    Example Requests:
        # Full search
        GET /api/search?q=cafe&lat=16.0544&lng=108.2428&radius=5&min_rating=4.0
        
        # Autocomplete (NEW V2)
        GET /v2/autocomplete?q=rest
        
        # Nearby
        GET /api/search/nearby?lat=16.0544&lng=108.2428&radius=2
        
        # By type
        GET /api/search/type/beach?lat=16.0544&lng=108.2428&radius=20
        
        # Popular
        GET /api/search/popular?lat=16.0544&lng=108.2428&limit=10
    """
    
    def __init__(self, search_service: SearchService):
        """Initialize controller with service dependency."""
        self.search_service = search_service
        self._register_routes()
        logger.info("[INFO] SearchController initialized")
    
    def _register_routes(self):
        """Register all routes with Flask Blueprint."""
        search_bp.add_url_rule("", "search", self.search, methods=["GET"])
        # REMOVED: /autocomplete route - Use /v2/autocomplete instead
        search_bp.add_url_rule("/nearby", "nearby", self.get_nearby, methods=["GET"])
        search_bp.add_url_rule("/type/<poi_type>", "by_type", self.get_by_type, methods=["GET"])
        search_bp.add_url_rule("/popular", "popular", self.get_popular, methods=["GET"])
    
    def search(self):
        """
        Full-text search with geo-distance and filters (Elasticsearch).
        
        Query Parameters:
            q (required): Search query (e.g., "vietnamese restaurant", "beach")
            lat (optional): Latitude for geo-distance sorting
            lng (optional): Longitude for geo-distance sorting
            radius (optional): Search radius in km (default: 10, max: 50)
            types (optional): Comma-separated types (e.g., "restaurant,cafe")
            min_rating (optional): Minimum rating (0-5)
            price_levels (optional): Comma-separated price levels (e.g., "MODERATE,INEXPENSIVE")
            sort_by (optional): Sort order - "relevance", "distance", "rating", "popularity" (default: relevance)
            limit (optional): Max results (default: 20, max: 100)
            offset (optional): Pagination offset (default: 0)
        
        Response Success (200):
            {
                "resultMessage": {"en": "...", "vn": "..."},
                "resultCode": "SEARCH_SUCCESS",
                "results": [POI objects with _score and _distance_km],
                "total": 45,
                "took_ms": 23,
                "source": "elasticsearch|mongodb",
                "page": 1,
                "limit": 20
            }
        
        Examples:
            # Search cafes near location
            GET /api/search?q=cafe&lat=16.0544&lng=108.2428&radius=5&min_rating=4.0
            
            # Search beaches (no location)
            GET /api/search?q=beach&types=beach&min_rating=4.5
            
            # Sort by rating
            GET /api/search?q=restaurant&sort_by=rating&limit=10
        """
        try:
            query = request.args.get('q', '').strip()
            lat = request.args.get('lat', type=float)
            lng = request.args.get('lng', type=float)
            radius = request.args.get('radius', default=10.0, type=float)
            types = request.args.get('types', '').strip()
            min_rating = request.args.get('min_rating', type=float)
            price_levels = request.args.get('price_levels', '').strip()
            sort_by = request.args.get('sort_by', default='relevance').strip()
            limit = request.args.get('limit', default=20, type=int)
            offset = request.args.get('offset', default=0, type=int)
            
            # Validate required parameters
            if not query:
                return build_error_response(
                    "Query parameter 'q' is required",
                    "Tham số 'q' là bắt buộc",
                    "MISSING_QUERY",
                    400
                )
            
            # Validate location if provided
            if (lat is None) != (lng is None):
                return build_error_response(
                    "Both latitude and longitude are required for geo search",
                    "Cả vĩ độ và kinh độ đều cần thiết cho tìm kiếm theo vị trí",
                    "INCOMPLETE_LOCATION",
                    400
                )
            
            if lat is not None and not (-90 <= lat <= 90):
                return build_error_response(
                    "Latitude must be between -90 and 90",
                    "Vĩ độ phải nằm trong khoảng -90 đến 90",
                    "INVALID_LATITUDE",
                    400
                )
            
            if lng is not None and not (-180 <= lng <= 180):
                return build_error_response(
                    "Longitude must be between -180 and 180",
                    "Kinh độ phải nằm trong khoảng -180 đến 180",
                    "INVALID_LONGITUDE",
                    400
                )
            
            # Validate other parameters
            if not (0.1 <= radius <= 50):
                return build_error_response(
                    "Radius must be between 0.1 and 50 km",
                    "Bán kính phải từ 0.1 đến 50 km",
                    "INVALID_RADIUS",
                    400
                )
            
            if not (1 <= limit <= 100):
                return build_error_response(
                    "Limit must be between 1 and 100",
                    "Giới hạn phải từ 1 đến 100",
                    "INVALID_LIMIT",
                    400
                )
            
            if offset < 0:
                return build_error_response(
                    "Offset must be non-negative",
                    "Offset phải không âm",
                    "INVALID_OFFSET",
                    400
                )
            
            if min_rating is not None and not (0 <= min_rating <= 5):
                return build_error_response(
                    "Minimum rating must be between 0 and 5",
                    "Đánh giá tối thiểu phải từ 0 đến 5",
                    "INVALID_MIN_RATING",
                    400
                )
            
            if sort_by not in ['relevance', 'distance', 'rating', 'popularity']:
                return build_error_response(
                    "Sort order must be 'relevance', 'distance', 'rating', or 'popularity'",
                    "Thứ tự sắp xếp phải là 'relevance', 'distance', 'rating' hoặc 'popularity'",
                    "INVALID_SORT",
                    400
                )
            
            # Parse lists
            types_list = [t.strip() for t in types.split(',') if t.strip()] if types else None
            price_levels_list = [p.strip() for p in price_levels.split(',') if p.strip()] if price_levels else None
            
            # Call service
            logger.info(f"[SEARCH] ES Search: q='{query}', lat={lat}, lng={lng}, radius={radius}km")
            
            result = self.search_service.search(
                query=query,
                latitude=lat,
                longitude=lng,
                radius_km=radius,
                types=types_list,
                min_rating=min_rating,
                price_levels=price_levels_list,
                sort_by=sort_by,
                limit=limit,
                offset=offset
            )
            return build_success_response(
                f"Found {result['total']} results in {result['took_ms']}ms",
                f"Tìm thấy {result['total']} kết quả trong {result['took_ms']}ms",
                "SEARCH_SUCCESS",
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
                "An error occurred while searching",
                "Đã xảy ra lỗi khi tìm kiếm",
                "SEARCH_ERROR",
                500
            )
    
    # NOTE: autocomplete() method REMOVED
    # Use /v2/autocomplete endpoint instead (autocomplete_controller.py)
    # Migration date: 2025-01
    
    def get_nearby(self):
        """
        Get POIs near a location (no text query).
        
        Query Parameters:
            lat (required): Latitude
            lng (required): Longitude
            radius (optional): Search radius in km (default: 5, max: 50)
            types (optional): Comma-separated types filter
            min_rating (optional): Minimum rating (0-5)
            limit (optional): Max results (default: 20, max: 100)
        
        Response Success (200):
            {
                "resultMessage": {"en": "...", "vn": "..."},
                "resultCode": "NEARBY_SUCCESS",
                "results": [POI objects with _distance_km],
                "total": 25,
                "center": {"latitude": 16.0544, "longitude": 108.2428},
                "radius_km": 5.0,
                "source": "elasticsearch|mongodb"
            }
        
        Examples:
            # Get all nearby POIs
            GET /api/search/nearby?lat=16.0544&lng=108.2428&radius=2
            
            # Filter by type and rating
            GET /api/search/nearby?lat=16.0544&lng=108.2428&radius=5&types=restaurant,cafe&min_rating=4.0
        """
        try:
            lat = request.args.get('lat', type=float)
            lng = request.args.get('lng', type=float)
            radius = request.args.get('radius', default=5.0, type=float)
            types = request.args.get('types', '').strip()
            min_rating = request.args.get('min_rating', type=float)
            limit = request.args.get('limit', default=20, type=int)
            
            # Validate required parameters
            if lat is None or lng is None:
                return build_error_response(
                    "Latitude and longitude are required",
                    "Vĩ độ và kinh độ là bắt buộc",
                    "MISSING_LOCATION",
                    400
                )
            
            # Validate ranges
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
            
            if not (1 <= limit <= 100):
                return build_error_response(
                    "Limit must be between 1 and 100",
                    "Giới hạn phải từ 1 đến 100",
                    "INVALID_LIMIT",
                    400
                )
            
            # Parse types
            types_list = [t.strip() for t in types.split(',') if t.strip()] if types else None
            
            # Call service
            logger.info(f"[LOCATION] Get nearby: lat={lat}, lng={lng}, radius={radius}km")
            
            result = self.search_service.get_nearby(
                latitude=lat,
                longitude=lng,
                radius_km=radius,
                types=types_list,
                min_rating=min_rating,
                limit=limit
            )
            return build_success_response(
                f"Found {result['total']} nearby places",
                f"Tìm thấy {result['total']} địa điểm gần đây",
                "NEARBY_SUCCESS",
                data=result,
                status_code=200
            )
        
        except Exception as e:
            logger.error(f"[ERROR] Get nearby failed: {e}", exc_info=True)
            return build_error_response(
                "An error occurred while getting nearby places",
                "Đã xảy ra lỗi khi lấy địa điểm gần đây",
                "NEARBY_ERROR",
                500
            )
    
    def get_by_type(self, poi_type: str):
        """
        Browse POIs by type/category.
        
        Path Parameters:
            poi_type: POI type (e.g., "beach", "restaurant", "museum")
        
        Query Parameters:
            lat (optional): Center latitude
            lng (optional): Center longitude
            radius (optional): Search radius in km
            min_rating (optional): Minimum rating (0-5)
            limit (optional): Max results (default: 20, max: 100)
        
        Response Success (200):
            {
                "resultMessage": {"en": "...", "vn": "..."},
                "resultCode": "TYPE_SEARCH_SUCCESS",
                "results": [POI objects],
                "total": 18,
                "type": "beach",
                "source": "elasticsearch|mongodb"
            }
        
        Examples:
            # Get all beaches
            GET /api/search/type/beach
            
            # Get restaurants near location
            GET /api/search/type/restaurant?lat=16.0544&lng=108.2428&radius=10&min_rating=4.0
        """
        try:
            # Validate poi_type
            if not poi_type or not poi_type.strip():
                return build_error_response(
                    "POI type is required",
                    "Loại địa điểm là bắt buộc",
                    "MISSING_TYPE",
                    400
                )
            lat = request.args.get('lat', type=float)
            lng = request.args.get('lng', type=float)
            radius = request.args.get('radius', type=float)
            min_rating = request.args.get('min_rating', type=float)
            limit = request.args.get('limit', default=20, type=int)
            
            # Validate location if provided
            if (lat is None) != (lng is None):
                return build_error_response(
                    "Both latitude and longitude are required",
                    "Cả vĩ độ và kinh độ đều cần thiết",
                    "INCOMPLETE_LOCATION",
                    400
                )
            
            # Call service
            logger.info(f"[SEARCH] Get by type: type='{poi_type}', lat={lat}, lng={lng}")
            
            result = self.search_service.get_by_type(
                poi_type=poi_type,
                latitude=lat,
                longitude=lng,
                radius_km=radius,
                min_rating=min_rating,
                limit=limit
            )
            return build_success_response(
                f"Found {result['total']} {poi_type} places",
                f"Tìm thấy {result['total']} địa điểm {poi_type}",
                "TYPE_SEARCH_SUCCESS",
                data=result,
                status_code=200
            )
        
        except Exception as e:
            logger.error(f"[ERROR] Get by type failed: {e}", exc_info=True)
            return build_error_response(
                "An error occurred while searching by type",
                "Đã xảy ra lỗi khi tìm kiếm theo loại",
                "TYPE_SEARCH_ERROR",
                500
            )
    
    def get_popular(self):
        """
        Get popular POIs (by rating + review count).
        
        Query Parameters:
            lat (optional): Center latitude
            lng (optional): Center longitude
            radius (optional): Search radius in km
            types (optional): Comma-separated types filter
            limit (optional): Max results (default: 20, max: 100)
        
        Response Success (200):
            {
                "resultMessage": {"en": "...", "vn": "..."},
                "resultCode": "POPULAR_SUCCESS",
                "results": [POI objects sorted by popularity],
                "total": 30,
                "source": "elasticsearch|mongodb"
            }
        
        Examples:
            # Get top popular POIs
            GET /api/search/popular?limit=10
            
            # Get popular restaurants near location
            GET /api/search/popular?lat=16.0544&lng=108.2428&radius=10&types=restaurant&limit=20
        """
        try:
            lat = request.args.get('lat', type=float)
            lng = request.args.get('lng', type=float)
            radius = request.args.get('radius', type=float)
            types = request.args.get('types', '').strip()
            limit = request.args.get('limit', default=20, type=int)
            
            # Validate location if provided
            if (lat is None) != (lng is None):
                return build_error_response(
                    "Both latitude and longitude are required",
                    "Cả vĩ độ và kinh độ đều cần thiết",
                    "INCOMPLETE_LOCATION",
                    400
                )
            
            # Parse types
            types_list = [t.strip() for t in types.split(',') if t.strip()] if types else None
            
            # Call service
            logger.info(f"[RATING] Get popular: lat={lat}, lng={lng}, types={types_list}")
            
            result = self.search_service.get_popular(
                latitude=lat,
                longitude=lng,
                radius_km=radius,
                types=types_list,
                limit=limit
            )
            return build_success_response(
                f"Found {result['total']} popular places",
                f"Tìm thấy {result['total']} địa điểm phổ biến",
                "POPULAR_SUCCESS",
                data=result,
                status_code=200
            )
        
        except Exception as e:
            logger.error(f"[ERROR] Get popular failed: {e}", exc_info=True)
            return build_error_response(
                "An error occurred while getting popular places",
                "Đã xảy ra lỗi khi lấy địa điểm phổ biến",
                "POPULAR_ERROR",
                500
            )


# Initialize controller with DI
def init_search_controller():
    """Initialize Search controller with dependency injection."""
    container = DIContainer.get_instance()
    search_service = container.resolve('SearchService')
    return SearchController(search_service)
