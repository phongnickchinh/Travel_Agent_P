"""
Core Module
============

Infrastructure components for the application:
- clients/: Database client connections (MongoDB, Redis, Elasticsearch)
- cache/: Caching utilities (Redis-based)
- rate_limiter/: API rate limiting

Base classes and DI:
- di_container: Dependency injection container
- di_setup: DI configuration and registration
- base_model: SQLAlchemy base model
- es_initializer: Elasticsearch index initialization

Usage:
    # Import specific items directly from submodules
    from app.core.clients.mongodb_client import get_mongodb_client
    from app.core.cache.redis_blacklist import RedisBlacklist
    from app.core.rate_limiter.rate_limiter import rate_limit
    
    # Or import from core (lazy loaded)
    from app.core import DIContainer
"""

# Only import non-dependent items at module level
from .di_container import DIContainer

# Other items should be imported directly from submodules
# to avoid circular imports and unnecessary loading

__all__ = [
    'DIContainer',
]
