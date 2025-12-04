"""
Circuit Breaker Pattern
========================

Purpose:
- Prevent cascading failures by failing fast when service is down
- Automatically recover when service becomes healthy
- Protect system from calling repeatedly failing services

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is failing, requests fail immediately (fail-fast)
- HALF_OPEN: Testing if service recovered, allow limited requests

Use Cases:
- External API calls (Google Places, OpenAI, TripAdvisor)
- Database connections
- Microservice communication

Author: Travel Agent P Team
Date: October 27, 2025
"""

import time
import logging
from enum import Enum
from functools import wraps
from typing import Callable, Type, Optional, Any
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Failing, reject requests immediately
    HALF_OPEN = "half_open"    # Testing recovery


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is OPEN."""
    pass


class CircuitBreaker:
    """
    Circuit Breaker implementation để protect khỏi cascading failures.
    
    How it works:
    1. CLOSED state: Normal operation
       - Requests pass through
       - Track failure count
       - If failures >= threshold → Open circuit
    
    2. OPEN state: Service is failing
       - Requests fail immediately (fail-fast)
       - Wait for timeout period
       - After timeout → Half-Open
    
    3. HALF_OPEN state: Testing recovery
       - Allow limited test requests
       - If success → Close circuit
       - If fail → Open circuit again
    
    Args:
        name: Circuit breaker name for logging
        failure_threshold: Number of failures before opening (default: 5)
        timeout: Seconds to wait before attempting recovery (default: 60)
        half_open_max_calls: Max calls allowed in half-open state (default: 1)
        expected_exception: Exception type to track (default: Exception)
        on_state_change: Optional callback when state changes
    
    Example:
        # Create circuit breaker
        breaker = CircuitBreaker(
            name="google_places_api",
            failure_threshold=5,
            timeout=60
        )
        
        @breaker
        def call_google_places():
            response = requests.get("https://maps.googleapis.com/...")
            response.raise_for_status()
            return response.json()
        
        # Use the protected function
        try:
            data = call_google_places()
        except CircuitBreakerOpenException:
            # Service is down, use fallback
            data = get_cached_data()
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: int = 60,
        half_open_max_calls: int = 1,
        expected_exception: Type[Exception] = Exception,
        on_state_change: Optional[Callable] = None
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls
        self.expected_exception = expected_exception
        self.on_state_change = on_state_change
        
        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None
        self.half_open_calls = 0
        
        # Thread safety
        self._lock = threading.Lock()
        
        logger.info(
            f"[CIRCUIT] Circuit Breaker '{self.name}' initialized: "
            f"threshold={failure_threshold}, timeout={timeout}s"
        )
    
    def _change_state(self, new_state: CircuitState):
        """Change circuit state and log transition."""
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            
            logger.info(
                f"[CIRCUIT] Circuit '{self.name}' state change: "
                f"{old_state.value.upper()} → {new_state.value.upper()}"
            )
            
            # Reset counters on state change
            if new_state == CircuitState.CLOSED:
                self.failure_count = 0
                self.success_count = 0
                self.half_open_calls = 0
            elif new_state == CircuitState.OPEN:
                self.opened_at = datetime.now()
                self.half_open_calls = 0
            elif new_state == CircuitState.HALF_OPEN:
                self.half_open_calls = 0
            
            # Call state change callback
            if self.on_state_change:
                try:
                    self.on_state_change(old_state, new_state)
                except Exception as e:
                    logger.error(f"[CIRCUIT] State change callback failed: {e}")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt circuit reset."""
        if self.opened_at is None:
            return True
        
        time_since_open = (datetime.now() - self.opened_at).total_seconds()
        return time_since_open >= self.timeout
    
    def _record_success(self):
        """Record successful call."""
        with self._lock:
            self.last_success_time = datetime.now()
            self.success_count += 1
            
            if self.state == CircuitState.HALF_OPEN:
                # Half-open test succeeded, close circuit
                logger.info(
                    f"[CIRCUIT] Circuit '{self.name}' recovery test succeeded, closing circuit"
                )
                self._change_state(CircuitState.CLOSED)
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
    
    def _record_failure(self, exception: Exception):
        """Record failed call."""
        with self._lock:
            self.last_failure_time = datetime.now()
            self.failure_count += 1
            
            logger.warning(
                f"[CIRCUIT] Circuit '{self.name}' failure {self.failure_count}/{self.failure_threshold}: "
                f"{type(exception).__name__}: {str(exception)}"
            )
            
            if self.state == CircuitState.HALF_OPEN:
                # Half-open test failed, reopen circuit
                logger.error(
                    f"[CIRCUIT] Circuit '{self.name}' recovery test failed, reopening circuit"
                )
                self._change_state(CircuitState.OPEN)
            
            elif self.state == CircuitState.CLOSED:
                # Check if threshold exceeded
                if self.failure_count >= self.failure_threshold:
                    logger.error(
                        f"[CIRCUIT] Circuit '{self.name}' opened after {self.failure_count} failures"
                    )
                    self._change_state(CircuitState.OPEN)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Raises:
            CircuitBreakerOpenException: If circuit is open
            Original exception: If function fails and circuit remains closed
        """
        with self._lock:
            # Check circuit state
            if self.state == CircuitState.OPEN:
                # Check if timeout elapsed
                if self._should_attempt_reset():
                    logger.info(
                        f"[CIRCUIT] Circuit '{self.name}' timeout elapsed, entering HALF_OPEN"
                    )
                    self._change_state(CircuitState.HALF_OPEN)
                else:
                    # Circuit still open, fail fast
                    time_remaining = self.timeout - (
                        datetime.now() - self.opened_at
                    ).total_seconds()
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.name}' is OPEN "
                        f"(retry in {time_remaining:.0f}s)"
                    )
            
            # Half-open: limit concurrent calls
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
                if self.half_open_calls > self.half_open_max_calls:
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.name}' is testing recovery "
                        f"(max {self.half_open_max_calls} test calls)"
                    )
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        
        except self.expected_exception as e:
            self._record_failure(e)
            raise
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator interface for circuit breaker."""
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            logger.info(f"[CIRCUIT] Circuit '{self.name}' manually reset to CLOSED")
            self._change_state(CircuitState.CLOSED)
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.opened_at = None
    
    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "failure_threshold": self.failure_threshold,
            "timeout": self.timeout
        }


# Global circuit breaker registry
_circuit_breakers = {}
_registry_lock = threading.Lock()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    timeout: int = 60,
    **kwargs
) -> CircuitBreaker:
    """
    Get or create a named circuit breaker (singleton per name).
    
    Example:
        breaker = get_circuit_breaker("google_places_api", failure_threshold=5)
        
        @breaker
        def call_api():
            ...
    """
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                timeout=timeout,
                **kwargs
            )
        return _circuit_breakers[name]


def get_all_circuit_breakers() -> dict:
    """Get state of all circuit breakers."""
    with _registry_lock:
        return {
            name: breaker.get_state()
            for name, breaker in _circuit_breakers.items()
        }


def reset_all_circuit_breakers():
    """Reset all circuit breakers to CLOSED state."""
    with _registry_lock:
        for breaker in _circuit_breakers.values():
            breaker.reset()


# Predefined circuit breakers for common services
class CircuitBreakers:
    """
    Predefined circuit breakers for common external services.
    
    Usage:
        @CircuitBreakers.GOOGLE_PLACES
        def fetch_places():
            ...
    """
    
    # Google Places API
    GOOGLE_PLACES = get_circuit_breaker(
        name="google_places_api",
        failure_threshold=5,
        timeout=60
    )
    
    # OpenAI API
    OPENAI = get_circuit_breaker(
        name="openai_api",
        failure_threshold=3,
        timeout=120
    )
    
    # TripAdvisor API
    TRIPADVISOR = get_circuit_breaker(
        name="tripadvisor_api",
        failure_threshold=5,
        timeout=60
    )
    
    # HuggingFace Inference API
    HUGGINGFACE = get_circuit_breaker(
        name="huggingface_api",
        failure_threshold=5,
        timeout=60
    )
    
    # MongoDB
    MONGODB = get_circuit_breaker(
        name="mongodb",
        failure_threshold=3,
        timeout=30
    )
    
    # Elasticsearch
    ELASTICSEARCH = get_circuit_breaker(
        name="elasticsearch",
        failure_threshold=5,
        timeout=60
    )


# Example usage
if __name__ == "__main__":
    import requests
    
    # Example 1: Basic usage
    breaker = CircuitBreaker(name="test_api", failure_threshold=3, timeout=10)
    
    @breaker
    def call_api():
        response = requests.get("https://httpbin.org/status/500")
        response.raise_for_status()
        return response.json()
    
    # Test circuit breaker
    for i in range(10):
        try:
            print(f"\nAttempt {i + 1}:")
            result = call_api()
            print(f"Success: {result}")
        except CircuitBreakerOpenException as e:
            print(f"Circuit OPEN: {e}")
        except Exception as e:
            print(f"Request failed: {e}")
        
        time.sleep(1)
    
    # Print final state
    print(f"\nFinal state: {breaker.get_state()}")
