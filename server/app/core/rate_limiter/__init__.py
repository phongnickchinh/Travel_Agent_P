"""
Rate Limiter Module
====================

Redis-based rate limiting for API endpoints:
- Sliding window algorithm
- Per-IP and per-user limiting
- Decorator-based implementation
"""

from .rate_limiter import (
    RateLimiter,
    rate_limit,
    get_identifier_by_email,
    get_identifier_by_user_id,
    get_identifier_from_auth_token
)

__all__ = [
    'RateLimiter',
    'rate_limit',
    'get_identifier_by_email',
    'get_identifier_by_user_id',
    'get_identifier_from_auth_token'
]
