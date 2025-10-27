"""
Cache Helper for Redis-based caching.

Provides decorators and utilities for caching function results in Redis.
"""
import json
import logging
import functools
from typing import Any, Callable, Optional, Union
from app.core.redis_client import get_redis
from config import Config

logger = logging.getLogger(__name__)


class CacheHelper:
    """Helper class for Redis caching operations."""
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not Config.CACHE_ENABLED:
            return None
            
        redis_client = get_redis()
        if not redis_client:
            return None
            
        try:
            value = redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error for key '{key}': {str(e)}")
            return None
    
    @staticmethod
    def set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (default: Config.CACHE_DEFAULT_TTL)
            
        Returns:
            True if successful, False otherwise
        """
        if not Config.CACHE_ENABLED:
            return False
            
        redis_client = get_redis()
        if not redis_client:
            return False
            
        try:
            ttl = ttl or Config.CACHE_DEFAULT_TTL
            serialized = json.dumps(value)
            redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key '{key}': {str(e)}")
            return False
    
    @staticmethod
    def delete(key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        redis_client = get_redis()
        if not redis_client:
            return False
            
        try:
            redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key '{key}': {str(e)}")
            return False
    
    @staticmethod
    def delete_pattern(pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., 'user:*')
            
        Returns:
            Number of keys deleted
        """
        redis_client = get_redis()
        if not redis_client:
            return 0
            
        try:
            keys = redis_client.keys(pattern)
            if keys:
                return redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache delete pattern error for '{pattern}': {str(e)}")
            return 0
    
    @staticmethod
    def exists(key: str) -> bool:
        """Check if key exists in cache."""
        redis_client = get_redis()
        if not redis_client:
            return False
            
        try:
            return bool(redis_client.exists(key))
        except:
            return False
    
    @staticmethod
    def build_key(*parts: str) -> str:
        """
        Build cache key from parts.
        
        Example:
            build_key('user', 'profile', '123') -> 'user:profile:123'
        """
        return ':'.join(str(part) for part in parts)


def cache_result(
    key_prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None
):
    """
    Decorator to cache function results in Redis.
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time-to-live in seconds
        key_builder: Optional function to build cache key from args/kwargs
                    Signature: key_builder(*args, **kwargs) -> str
    
    Example:
        @cache_result('user:profile', ttl=600)
        def get_user_profile(user_id):
            return {'id': user_id, 'name': 'John'}
        
        # Custom key builder
        def build_key(user_id, include_posts=False):
            return f"user:{user_id}:posts:{include_posts}"
        
        @cache_result('user', key_builder=build_key)
        def get_user_data(user_id, include_posts=False):
            return load_user(user_id, include_posts)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                try:
                    key_suffix = key_builder(*args, **kwargs)
                    cache_key = CacheHelper.build_key(key_prefix, key_suffix)
                except Exception as e:
                    logger.warning(f"Key builder error: {str(e)}, falling back to default")
                    cache_key = CacheHelper.build_key(key_prefix, str(args), str(kwargs))
            else:
                # Default: use function args as key
                cache_key = CacheHelper.build_key(key_prefix, str(args), str(kwargs))
            
            # Try to get from cache
            cached = CacheHelper.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return cached
            
            # Execute function and cache result
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)
            
            # Cache the result
            CacheHelper.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(key_pattern: str):
    """
    Decorator to invalidate cache after function execution.
    
    Args:
        key_pattern: Pattern to match keys for deletion (e.g., 'user:*')
    
    Example:
        @invalidate_cache('user:profile:*')
        def update_user_profile(user_id, data):
            # Update database
            return updated_user
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Invalidate cache after successful execution
            deleted = CacheHelper.delete_pattern(key_pattern)
            if deleted > 0:
                logger.info(f"Invalidated {deleted} cache keys matching '{key_pattern}'")
            
            return result
        
        return wrapper
    return decorator
