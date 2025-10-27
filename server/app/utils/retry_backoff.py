"""
Retry with Exponential Backoff
================================

Purpose:
- Automatically retry failed operations with increasing delays
- Prevent overwhelming failing services
- Configurable retry attempts and delay strategy

Use Cases:
- External API calls (Google Places, OpenAI, TripAdvisor)
- Database connection retries
- Network requests

Author: Travel Agent P Team
Date: October 27, 2025
"""

import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional, Any
import random

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for automatic retry với exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 60.0)
        exponential_base: Base for exponential calculation (default: 2.0)
        jitter: Add random jitter to prevent thundering herd (default: True)
        exceptions: Tuple of exceptions to catch and retry (default: all Exception)
        on_retry: Optional callback function called on each retry
                  Signature: on_retry(attempt, exception, delay)
    
    Returns:
        Decorated function that retries on failure
    
    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def call_google_places_api():
            response = requests.get("https://maps.googleapis.com/...")
            response.raise_for_status()
            return response.json()
        
        # Retry sequence with exponential backoff:
        # Attempt 1: Immediate
        # Attempt 2: Wait 1s (base_delay)
        # Attempt 3: Wait 2s (base_delay * 2^1)
        # Attempt 4: Wait 4s (base_delay * 2^2)
        # After 4 attempts: Raise exception
    
    Backoff Formula:
        delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
        if jitter:
            delay = delay * (0.5 + random.random() * 0.5)  # ±25% jitter
    
    Jitter Benefits:
        - Prevents "thundering herd" problem
        - Distributes retry attempts over time
        - Reduces load spikes on recovering services
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            last_exception = None
            
            while attempt <= max_retries:
                try:
                    # Log attempt
                    if attempt > 0:
                        logger.info(
                            f"🔄 Retry attempt {attempt}/{max_retries} for {func.__name__}"
                        )
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Success - log recovery if this was a retry
                    if attempt > 0:
                        logger.info(
                            f"✅ {func.__name__} succeeded after {attempt} retries"
                        )
                    
                    return result
                
                except exceptions as e:
                    last_exception = e
                    attempt += 1
                    
                    # Check if we should retry
                    if attempt > max_retries:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if jitter:
                        # Jitter range: [50%, 150%] of calculated delay
                        delay = delay * (0.5 + random.random())
                    
                    # Log retry information
                    logger.warning(
                        f"⚠️ {func.__name__} failed (attempt {attempt}/{max_retries}), "
                        f"retrying in {delay:.2f}s: {type(e).__name__}: {str(e)}"
                    )
                    
                    # Call optional retry callback
                    if on_retry:
                        try:
                            on_retry(attempt, e, delay)
                        except Exception as callback_error:
                            logger.error(
                                f"❌ Retry callback failed: {callback_error}"
                            )
                    
                    # Wait before retry
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def retry_async_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Async version of retry_with_backoff for async functions.
    
    Example:
        @retry_async_with_backoff(max_retries=3)
        async def fetch_data():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.json()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            import asyncio
            
            attempt = 0
            last_exception = None
            
            while attempt <= max_retries:
                try:
                    if attempt > 0:
                        logger.info(
                            f"🔄 Retry attempt {attempt}/{max_retries} for {func.__name__}"
                        )
                    
                    result = await func(*args, **kwargs)
                    
                    if attempt > 0:
                        logger.info(
                            f"✅ {func.__name__} succeeded after {attempt} retries"
                        )
                    
                    return result
                
                except exceptions as e:
                    last_exception = e
                    attempt += 1
                    
                    if attempt > max_retries:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise
                    
                    delay = min(
                        base_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )
                    
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(
                        f"⚠️ {func.__name__} failed (attempt {attempt}/{max_retries}), "
                        f"retrying in {delay:.2f}s: {type(e).__name__}: {str(e)}"
                    )
                    
                    await asyncio.sleep(delay)
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


# Predefined retry strategies for common scenarios
class RetryStrategies:
    """
    Predefined retry strategies for common use cases.
    
    Usage:
        @RetryStrategies.API_CALL
        def fetch_external_data():
            ...
    """
    
    # Quick retries for fast APIs (3 retries, max 10s total)
    FAST_API = retry_with_backoff(
        max_retries=3,
        base_delay=0.5,
        max_delay=5.0,
        exponential_base=2.0
    )
    
    # Standard retries for external APIs (5 retries, max ~30s total)
    API_CALL = retry_with_backoff(
        max_retries=5,
        base_delay=1.0,
        max_delay=15.0,
        exponential_base=2.0
    )
    
    # Aggressive retries for critical operations (10 retries, max ~2min total)
    CRITICAL = retry_with_backoff(
        max_retries=10,
        base_delay=1.0,
        max_delay=30.0,
        exponential_base=2.0
    )
    
    # Conservative retries for expensive operations (3 retries, max ~5min total)
    EXPENSIVE = retry_with_backoff(
        max_retries=3,
        base_delay=10.0,
        max_delay=60.0,
        exponential_base=2.0
    )
    
    # Database connection retries (5 retries, fast)
    DATABASE = retry_with_backoff(
        max_retries=5,
        base_delay=0.5,
        max_delay=5.0,
        exponential_base=2.0,
        exceptions=(ConnectionError, TimeoutError)
    )


# Example usage
if __name__ == "__main__":
    import requests
    
    # Example 1: Simple retry
    @retry_with_backoff(max_retries=3)
    def fetch_data():
        response = requests.get("https://httpbin.org/status/500")
        response.raise_for_status()
        return response.json()
    
    # Example 2: Custom retry callback
    def on_retry_callback(attempt, exception, delay):
        print(f"Custom callback: Attempt {attempt} failed with {exception}")
    
    @retry_with_backoff(max_retries=3, on_retry=on_retry_callback)
    def fetch_with_callback():
        raise Exception("Test exception")
    
    # Example 3: Using predefined strategy
    @RetryStrategies.API_CALL
    def call_external_api():
        response = requests.get("https://api.example.com/data")
        response.raise_for_status()
        return response.json()
    
    # Test retry logic
    try:
        print("Testing retry with backoff...")
        fetch_data()
    except Exception as e:
        print(f"Failed after all retries: {e}")
