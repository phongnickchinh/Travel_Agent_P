"""
Rate Limiter using Redis.

Implements sliding window rate limiting with Redis for API endpoints.
"""
import time
import logging
import functools
from typing import Callable, Optional
from flask import request, jsonify
import jwt
from config import Config
from app.core.clients.redis_client import get_redis

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter using sliding window algorithm."""
    
    @staticmethod
    def check_rate_limit(
        identifier: str,
        max_requests: int,
        window_seconds: int,
        redis_client=None
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Unique identifier (e.g., IP address, user ID)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            redis_client: Redis client (optional, will get default if None)
        
        Returns:
            Tuple of (is_allowed, info_dict)
            info_dict contains: remaining, reset_at, limit
        """
        if not Config.RATE_LIMIT_ENABLED:
            return True, {
                'remaining': max_requests,
                'limit': max_requests,
                'reset_at': None
            }
        
        redis_client = redis_client or get_redis()
        if not redis_client:
            # Fail open if Redis unavailable
            logger.warning("Rate limiter: Redis unavailable, allowing request")
            return True, {'remaining': max_requests, 'limit': max_requests, 'reset_at': None}
        
        try:
            current_time = time.time()
            window_start = current_time - window_seconds
            key = f"rate_limit:{identifier}"
            
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()
            
            # Remove old requests outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiry on key
            pipe.expire(key, window_seconds)
            
            # Execute pipeline
            results = pipe.execute()
            request_count = results[1]  # Result of zcard
            
            # Check if limit exceeded
            is_allowed = request_count < max_requests
            remaining = max(0, max_requests - request_count - 1)
            reset_at = int(current_time + window_seconds)
            
            info = {
                'remaining': remaining,
                'limit': max_requests,
                'reset_at': reset_at,
                'current_count': request_count
            }
            
            if not is_allowed:
                logger.warning(
                    f"Rate limit exceeded for {identifier}: "
                    f"{request_count}/{max_requests} in {window_seconds}s"
                )
            
            return is_allowed, info
            
        except Exception as e:
            logger.error(f"Rate limiter error: {str(e)}")
            # Fail open on error
            return True, {'remaining': max_requests, 'limit': max_requests, 'reset_at': None}
    
    @staticmethod
    def reset_rate_limit(identifier: str) -> bool:
        """
        Reset rate limit for identifier.
        
        Args:
            identifier: Unique identifier
            
        Returns:
            True if successful
        """
        redis_client = get_redis()
        if not redis_client:
            return False
        
        try:
            key = f"rate_limit:{identifier}"
            redis_client.delete(key)
            logger.info(f"Rate limit reset for {identifier}")
            return True
        except Exception as e:
            logger.error(f"Rate limit reset error: {str(e)}")
            return False


def rate_limit(
    max_requests: int,
    window_seconds: int,
    identifier_func: Optional[Callable] = None,
    key_prefix: str = ""
):
    """
    Decorator for rate limiting Flask endpoints.
    
    Args:
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        identifier_func: Optional function to extract identifier from request
                        Default: uses IP address
                        Signature: identifier_func() -> str
        key_prefix: Optional prefix for rate limit key (e.g., 'login', 'register')
    
    Example:
        # Rate limit by IP
        @rate_limit(max_requests=5, window_seconds=60)
        @app.route('/api/login')
        def login():
            return "OK"
        
        # Rate limit by user ID
        def get_user_id():
            return g.current_user.id if hasattr(g, 'current_user') else request.remote_addr
        
        @rate_limit(max_requests=10, window_seconds=3600, identifier_func=get_user_id)
        @app.route('/api/sensitive')
        def sensitive_action():
            return "OK"
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get identifier
            if identifier_func:
                try:
                    identifier = identifier_func()
                except Exception as e:
                    logger.warning(f"Identifier function error: {str(e)}, using IP")
                    identifier = request.remote_addr or 'unknown'
            else:
                identifier = request.remote_addr or 'unknown'
            
            # Add prefix if provided
            if key_prefix:
                identifier = f"{key_prefix}:{identifier}"
            
            # Check rate limit
            is_allowed, info = RateLimiter.check_rate_limit(
                identifier=identifier,
                max_requests=max_requests,
                window_seconds=window_seconds
            )
            
            # Add rate limit headers to response
            response_data = None
            if not is_allowed:
                response_data = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Try again in {window_seconds} seconds.',
                    'retry_after': window_seconds,
                    'limit': info['limit'],
                    'reset_at': info['reset_at']
                })
                response = response_data
                response.status_code = 429
            else:
                # Execute the wrapped function
                response = func(*args, **kwargs)
            
            # Add rate limit headers (works for both allowed and denied)
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(info['limit'])
                response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
                if info.get('reset_at'):
                    response.headers['X-RateLimit-Reset'] = str(info['reset_at'])
            
            return response
        
        return wrapper
    return decorator


def get_identifier_by_email():
    """Helper to get identifier from request JSON email field."""
    try:
        data = request.get_json()
        if data and 'email' in data:
            return f"email:{data['email']}"
    except:
        pass
    return request.remote_addr or 'unknown'


def get_identifier_by_user_id():
    """Helper to get identifier from current user ID in Flask g object."""
    from flask import g
    try:
        if hasattr(g, 'current_user') and g.current_user:
            return f"user:{g.current_user.id}"
    except:
        pass
    return request.remote_addr or 'unknown'


def get_identifier_from_auth_token():
    """Extract user ID from Authorization bearer token if present.

    Falls back to IP address if token absent or invalid.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return request.remote_addr or 'unknown'
    try:
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        if user_id:
            return f"user:{user_id}"
    except Exception:
        pass
    return request.remote_addr or 'unknown'
