"""
Redis Client Configuration and Connection Management.

This module provides a centralized Redis client that can be used across
the application for caching, rate limiting, and queue operations.
"""
import redis
import logging
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)


class RedisClient:
    """Singleton Redis client wrapper."""
    
    _instance: Optional[redis.Redis] = None
    _initialized = False
    
    @classmethod
    def get_instance(cls) -> redis.Redis:
        """
        Get Redis client instance (Singleton pattern).
        
        Returns:
            redis.Redis: Redis client instance
            
        Raises:
            ConnectionError: If cannot connect to Redis
        """
        if cls._instance is None:
            try:
                cls._instance = redis.Redis(
                    host=Config.REDIS_HOST,
                    port=Config.REDIS_PORT,
                    db=Config.REDIS_DB,
                    password=Config.REDIS_PASSWORD if hasattr(Config, 'REDIS_PASSWORD') else None,
                    decode_responses=True,  # Auto decode bytes to strings
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    health_check_interval=30
                )
                
                # Test connection
                cls._instance.ping()
                cls._initialized = True
                logger.info(f"[REDIS] Connected: {Config.REDIS_HOST}:{Config.REDIS_PORT}")
                
            except redis.ConnectionError as e:
                logger.error(f"[REDIS] Connection failed: {str(e)}")
                logger.warning("[REDIS] Application will continue without Redis (degraded mode)")
                cls._instance = None
                
        return cls._instance
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Redis is available and connected."""
        if cls._instance is None:
            return False
        try:
            cls._instance.ping()
            return True
        except:
            return False
    
    @classmethod
    def close(cls):
        """Close Redis connection."""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
            cls._initialized = False
            logger.info("Redis connection closed")


def get_redis() -> Optional[redis.Redis]:
    """
    Get Redis client instance.
    
    Returns:
        Optional[redis.Redis]: Redis client or None if unavailable
    """
    return RedisClient.get_instance()
