"""
Autocomplete Controller v2 - Hybrid Autocomplete API Endpoints
===============================================================

Purpose:
- Fast autocomplete with ES cache + Google fallback
- Click-to-resolve for fetching full POI details
- Cost-effective: ES (~$0) + Google Autocomplete (~$2.83/1000)
- Auto-enriching database from user searches

Security Features:
- Rate limiting per IP (Layer 1)
- Query validation and sanitization (Layer 2 support)
- Daily API quota enforcement (Layer 3 support)

Author: Travel Agent P Team
Date: December 22, 2025
Updated: December 23, 2025 (Anti-abuse protection)
"""

from flask import request, jsonify
import logging
import re

from . import autocomplete_bp
from app.service.autocomplete_service import AutocompleteService
from app.utils.response_helpers import build_error_response, build_success_response
from app.core.di_container import DIContainer
from app.core.rate_limiter import rate_limit
from app.core.clients.redis_client import get_redis
from config import Config

logger = logging.getLogger(__name__)


def get_client_ip():
    """Get client IP address for rate limiting."""
    # Check for forwarded IP (behind proxy/load balancer)
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        # Get first IP in the chain (original client)
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'

def init_autocomplete_controller():
    """Initialize Autocomplete controller with DI."""
    try:
        container = DIContainer.get_instance()
        service = container.get_autocomplete_service()
        controller = AutocompleteController(service)
        logger.info("[INFO] AutocompleteController v2 initialized")
    except Exception as e:
        logger.error(f"[ERROR] Failed to initialize AutocompleteController: {e}")
        raise


class AutocompleteController:
    """
    Autocomplete Controller v2 - Hybrid ES + Google Autocomplete
    
    Endpoints:
    - GET /api/v2/autocomplete - Search with hybrid strategy
    - POST /api/v2/autocomplete/resolve - Resolve place_id to full details
    - GET /api/v2/autocomplete/stats - Cache statistics (admin)
    
    Example Requests:
        # Autocomplete search
        GET /api/v2/autocomplete?q=Paris&limit=5
        
        # With location bias
        GET /api/v2/autocomplete?q=restaurant&lat=16.0544&lng=108.2428
        
        # With type filter
        GET /api/v2/autocomplete?q=beach&types=natural_feature,point_of_interest
        
        # Resolve place to full details
        POST /api/v2/autocomplete/resolve
        Body: {"place_id": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ"}
    """
    
    def __init__(self, autocomplete_service: AutocompleteService):
        """Initialize controller with service dependency."""
        self.service = autocomplete_service
        self._register_routes()
        logger.info("[INFO] AutocompleteController v2 routes registered")
    
    
    def _register_routes(self):
        """Register all routes with Flask Blueprint."""
        autocomplete_bp.add_url_rule(
            "", 
            "autocomplete", 
            self._wrap_rate_limit(self.autocomplete), 
            methods=["GET"]
        )
        autocomplete_bp.add_url_rule(
            "/resolve", 
            "resolve", 
            self.resolve, 
            methods=["POST"]
        )
        autocomplete_bp.add_url_rule(
            "/stats", 
            "stats", 
            self.get_stats, 
            methods=["GET"]
        )


    def autocomplete(self):
        """
        Hybrid autocomplete with ES cache + Google fallback.
        
        Query Parameters:
            q (required): Search query (min 1 char)
            limit (optional): Max results (default: 10, max: 20)
            types (optional): Comma-separated place types to filter
            lat (optional): Latitude for location bias
            lng (optional): Longitude for location bias
            session_token (optional): Google session token for billing
        
        Response Success (200):
            {
                "resultCode": "AUTOCOMPLETE_SUCCESS",
                "resultMessage": {"en": "...", "vn": "..."},
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
                "total": 5,
                "sources": {"es": 3, "google": 2, "mongodb": 0},
                "query_time_ms": 15.5
            }
        
        Response Error (400):
            {
                "resultCode": "VALIDATION_ERROR",
                "resultMessage": {"en": "Query is required", "vn": "..."}
            }
        """
        try:
            # Get and sanitize query parameter
            raw_query = request.args.get("q", "")
            query = self._sanitize_query(raw_query)
            
            # Validate query
            is_valid, error_msg = self._is_valid_query(query)
            if not is_valid:
                return build_error_response(
                    result_code="VALIDATION_ERROR",
                    message_en=error_msg,
                    message_vn="Tham số tìm kiếm không hợp lệ",
                    status_code=400
                )
            
            # Check negative query rate limit (anti-abuse)
            is_allowed, remaining = self._check_negative_query_limit()
            if not is_allowed:
                logger.warning(
                    f"[RATE_LIMIT] Negative query limit exceeded for client: {get_client_ip()}"
                )
                return build_error_response(
                    result_code="RATE_LIMIT_EXCEEDED",
                    message_en="Too many failed searches. Please wait a moment.",
                    message_vn="Quá nhiều tìm kiếm thất bại. Vui lòng đợi một chút.",
                    status_code=429
                )
            
            # Parse parameters
            limit = min(int(request.args.get("limit", 10)), 20)
            
            types_param = request.args.get("types", "")
            types = [t.strip() for t in types_param.split(",") if t.strip()] or None
            
            lat = request.args.get("lat", type=float)
            lng = request.args.get("lng", type=float)
            location = {"latitude": lat, "longitude": lng} if lat and lng else None
            
            session_token = request.args.get("session_token")
            
            # Call service
            result = self.service.autocomplete(
                query=query,
                limit=limit,
                types=types,
                location=location,
                session_token=session_token
            )
            
            # Track negative queries (ES miss = potential abuse pattern)
            # Increment counter when ES returns 0 results
            if result["sources"]["es"] == 0 and result["sources"]["mongodb"] == 0 and result["sources"]["google"] == 0:
                self._increment_negative_query_count()
            
            return build_success_response(
                result_code="AUTOCOMPLETE_SUCCESS",
                message_en=f"Found {result['total']} suggestions",
                message_vn=f"Tìm thấy {result['total']} gợi ý",
                data={
                    "suggestions": result["suggestions"],
                    "total": result["total"],
                    "sources": result["sources"],
                    "query_time_ms": result["query_time_ms"]
                }
            )
            
        except ValueError as e:
            logger.warning(f"[AUTOCOMPLETE] Validation error: {e}")
            return build_error_response(
                result_code="VALIDATION_ERROR",
                message_en=str(e),
                message_vn="Lỗi tham số đầu vào",
                status_code=400
            )
        except Exception as e:
            logger.error(f"[AUTOCOMPLETE] Error: {e}", exc_info=True)
            return build_error_response(
                result_code="INTERNAL_ERROR",
                message_en="Autocomplete search failed",
                message_vn="Lỗi tìm kiếm autocomplete",
                status_code=500
            )
    
    
    def resolve(self):
        """
        Resolve place_id to full POI details.
        
        Called when user CLICKS on an autocomplete suggestion.
        
        Request Body:
            {
                "place_id": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ" (required)
            }
        
        Response Success (200):
            {
                "resultCode": "RESOLVE_SUCCESS",
                "resultMessage": {"en": "...", "vn": "..."},
                "poi": {
                    "place_id": "...",
                    "name": "Paris",
                    "formatted_address": "...",
                    "location": {"latitude": ..., "longitude": ...},
                    ...
                }
            }
        
        Response Error (404):
            {
                "resultCode": "NOT_FOUND",
                "resultMessage": {"en": "Place not found", "vn": "..."}
            }
        """
        try:
            data = request.get_json() or {}
            place_id = data.get("place_id", "").strip()
            
            if not place_id:
                return build_error_response(
                    result_code="VALIDATION_ERROR",
                    message_en="place_id is required",
                    message_vn="place_id là bắt buộc",
                    status_code=400
                )
            
            # Call service to resolve
            poi = self.service.resolve(place_id)
            
            if not poi:
                return build_error_response(
                    result_code="NOT_FOUND",
                    message_en=f"Place with ID '{place_id}' not found",
                    message_vn=f"Không tìm thấy địa điểm với ID '{place_id}'",
                    status_code=404
                )
            
            return build_success_response(
                result_code="RESOLVE_SUCCESS",
                message_en="Place resolved successfully",
                message_vn="Đã lấy thông tin địa điểm thành công",
                data={"poi": poi}
            )
            
        except Exception as e:
            logger.error(f"[RESOLVE] Error: {e}", exc_info=True)
            return build_error_response(
                result_code="INTERNAL_ERROR",
                message_en="Failed to resolve place",
                message_vn="Lỗi khi lấy thông tin địa điểm",
                status_code=500
            )
    
    
    def get_stats(self):
        """
        Get autocomplete cache statistics (admin endpoint).
        
        Response (200):
            {
                "resultCode": "STATS_SUCCESS",
                "stats": {
                    "es_enabled": true,
                    "mongodb_count": 1234,
                    "es_count": 1200,
                    "pending_count": 456,
                    "cached_count": 778,
                    "quota": {
                        "google_api_calls_today": 150,
                        "google_api_daily_limit": 1000,
                        "quota_remaining": 850,
                        "quota_exhausted": false,
                        "quota_percentage": 15.0
                    }
                }
            }
        """
        try:
            stats = self.service.get_stats()
            
            # Add quota stats
            quota_stats = self.service.get_quota_stats()
            stats["quota"] = quota_stats
            
            return build_success_response(
                result_code="STATS_SUCCESS",
                message_en="Cache statistics retrieved",
                message_vn="Đã lấy thống kê cache",
                data={"stats": stats}
            )
            
        except Exception as e:
            logger.error(f"[STATS] Error: {e}", exc_info=True)
            return build_error_response(
                result_code="INTERNAL_ERROR",
                message_en="Failed to get statistics",
                message_vn="Lỗi khi lấy thống kê",
                status_code=500
            )

    
    def _wrap_rate_limit(self, func):
        """Wrap endpoint with rate limiting decorator."""
        @rate_limit(
            max_requests=Config.RATE_LIMIT_AUTOCOMPLETE,  # 30 req/min total
            window_seconds=Config.RATE_LIMIT_AUTOCOMPLETE_WINDOW,
            identifier_func=get_client_ip,
            key_prefix='autocomplete'
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        # Preserve function name for Flask
        wrapper.__name__ = func.__name__
        return wrapper
    
    
    def _check_negative_query_limit(self) -> tuple[bool, int]:
        """
        Check if client exceeded negative query limit.
        
        Negative queries are those that return 0 results from ES cache
        and would trigger Google API calls.
        
        Returns:
            (is_allowed, remaining_count)
        """
        try:
            redis = get_redis()
            if not redis:
                return True, Config.RATE_LIMIT_NEGATIVE_QUERY
            
            client_ip = get_client_ip()
            key = f"autocomplete:negative_limit:{client_ip}"
            
            current = redis.get(key)
            count = int(current) if current else 0
            
            if count >= Config.RATE_LIMIT_NEGATIVE_QUERY:
                return False, 0
            
            return True, Config.RATE_LIMIT_NEGATIVE_QUERY - count
        except Exception as e:
            logger.warning(f"[RATE_LIMIT] Failed to check negative limit: {e}")
            return True, Config.RATE_LIMIT_NEGATIVE_QUERY
    
    
    def _increment_negative_query_count(self) -> None:
        """
        Increment negative query counter for current client.
        Called when a query returns 0 ES results (potential Google API call).
        """
        try:
            redis = get_redis()
            if not redis:
                return
            
            client_ip = get_client_ip()
            key = f"autocomplete:negative_limit:{client_ip}"
            
            pipe = redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, Config.RATE_LIMIT_NEGATIVE_QUERY_WINDOW)
            pipe.execute()
            
            logger.debug(f"[RATE_LIMIT] Incremented negative query count for {client_ip}")
        except Exception as e:
            logger.warning(f"[RATE_LIMIT] Failed to increment negative count: {e}")
    
    
    @staticmethod
    def _sanitize_query(query: str) -> str:
        """
        Sanitize and validate query string.
        
        - Remove control characters
        - Trim whitespace
        - Limit length to 100 chars
        """
        if not query:
            return ""
        # Remove control characters
        query = re.sub(r'[\x00-\x1F\x7F]', '', query)
        # Trim and limit length
        return query.strip()[:100]
    
    
    @staticmethod
    def _is_valid_query(query: str) -> tuple[bool, str]:
        """
        Validate query for basic sanity checks.
        
        Returns:
            (is_valid, error_message)
        """
        if not query:
            return False, "Query is required"
        
        if len(query) < 2:
            return False, "Query must be at least 2 characters"
        
        if len(query) > 100:
            return False, "Query too long (max 100 characters)"
        
        # Block pure numeric queries (unlikely place names)
        if query.isdigit():
            return False, "Query cannot be purely numeric"
        
        return True, ""


