"""
Redis-based JWT Blacklist.

Replaces database-based blacklist with Redis for better performance.
Uses TTL for automatic cleanup - no cron job needed.
"""
import logging
from typing import Optional
from datetime import datetime, timedelta, timezone
from app.core.clients.redis_client import get_redis
from config import Config

logger = logging.getLogger(__name__)


class RedisBlacklist:
    """Redis-based JWT token blacklist."""
    
    KEY_PREFIX = "blacklist"
    
    @staticmethod
    def _build_key(token: str) -> str:
        """Build Redis key for token."""
        return f"{RedisBlacklist.KEY_PREFIX}:{token}"
    
    @staticmethod
    def add_token(
        token: str,
        user_id: int,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Add token to blacklist.
        
        Args:
            token: JWT token to blacklist
            user_id: User ID who owns the token
            expires_at: Token expiration datetime (for TTL calculation)
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"[BLACKLIST] Attempting to blacklist token for user {user_id}")
        
        redis_client = get_redis()
        if not redis_client:
            logger.error("[BLACKLIST] Redis unavailable - cannot blacklist token")
            return False
        
        try:
            logger.info(f"[BLACKLIST] Redis client available, building key...")
            key = RedisBlacklist._build_key(token)
            logger.info(f"[BLACKLIST] Key built: {key[:50]}...")
            
            # Calculate TTL based on token expiration
            if expires_at:
                # Use timezone-aware datetime to match expires_at
                now = datetime.now(timezone.utc)
                ttl_seconds = int((expires_at - now).total_seconds())
                
                logger.info(f"[BLACKLIST] Token expires at: {expires_at}, TTL: {ttl_seconds}s")
                
                # Ensure TTL is positive
                if ttl_seconds <= 0:
                    logger.warning(f"[BLACKLIST] Token already expired for user {user_id}, using fallback TTL")
                    ttl_seconds = 60  # Keep for 1 minute anyway
            else:
                # Default TTL if expiration not provided
                # Use the longer of access or refresh token expiry
                ttl_seconds = max(
                    Config.ACCESS_TOKEN_EXPIRE_SEC,
                    Config.REFRESH_TOKEN_EXPIRE_SEC
                )
                logger.info(f"[BLACKLIST] No expiry provided, using default TTL: {ttl_seconds}s")
            
            # Store with user_id as value and TTL
            logger.info(f"[BLACKLIST] Calling redis.setex(key={key[:50]}..., ttl={ttl_seconds}, value={user_id})")
            redis_client.setex(
                key,
                ttl_seconds,
                str(user_id)
            )
            
            logger.info(f"[BLACKLIST] Token blacklisted successfully for user {user_id} (TTL: {ttl_seconds}s)")
            
            # Verify it was actually set
            verify = redis_client.exists(key)
            logger.info(f"[BLACKLIST] Verification check: token exists in Redis = {verify}")
            
            return True
            
        except Exception as e:
            logger.error(f"[BLACKLIST] Error blacklisting token: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    def is_blacklisted(token: str) -> bool:
        """
        Check if token is blacklisted.
        
        Args:
            token: JWT token to check
        
        Returns:
            True if blacklisted, False otherwise
        """
        redis_client = get_redis()
        if not redis_client:
            # Fail closed - if Redis is down, consider all tokens valid
            # This allows graceful degradation
            logger.warning("Redis unavailable - assuming token is not blacklisted")
            return False
        
        try:
            key = RedisBlacklist._build_key(token)
            exists = redis_client.exists(key)
            
            if exists:
                logger.debug(f"Token is blacklisted")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking blacklist: {str(e)}")
            # Fail open on error
            return False
    
    @staticmethod
    def remove_token(token: str) -> bool:
        """
        Remove token from blacklist (rarely needed).
        
        Args:
            token: JWT token to remove
        
        Returns:
            True if successful
        """
        redis_client = get_redis()
        if not redis_client:
            return False
        
        try:
            key = RedisBlacklist._build_key(token)
            redis_client.delete(key)
            logger.info(f"Token removed from blacklist")
            return True
        except Exception as e:
            logger.error(f"Error removing token from blacklist: {str(e)}")
            return False
    
    @staticmethod
    def get_blacklist_count() -> int:
        """
        Get total number of blacklisted tokens.
        
        Returns:
            Number of blacklisted tokens
        """
        redis_client = get_redis()
        if not redis_client:
            return 0
        
        try:
            pattern = f"{RedisBlacklist.KEY_PREFIX}:*"
            keys = redis_client.keys(pattern)
            return len(keys)
        except Exception as e:
            logger.error(f"Error counting blacklisted tokens: {str(e)}")
            return 0
    
    @staticmethod
    def clear_all_blacklist() -> int:
        """
        Clear all blacklisted tokens (admin function).
        
        Returns:
            Number of tokens cleared
        """
        redis_client = get_redis()
        if not redis_client:
            return 0
        
        try:
            pattern = f"{RedisBlacklist.KEY_PREFIX}:*"
            keys = redis_client.keys(pattern)
            if keys:
                count = redis_client.delete(*keys)
                logger.warning(f"[BLACKLIST] Cleared {count} blacklisted tokens")
                return count
            return 0
        except Exception as e:
            logger.error(f"Error clearing blacklist: {str(e)}")
            return 0
