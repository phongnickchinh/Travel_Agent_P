"""
Core Module
============

Infrastructure components for the application:
- di/: Dependency injection container and setup
- clients/: Database client connections (MongoDB, Redis, Elasticsearch)
- cache/: Caching utilities (Redis-based)
- rate_limiter/: API rate limiting

Base classes:
- base_model: SQLAlchemy base model
- es_initializer: Elasticsearch index initialization

Usage:
    # Import specific items directly from submodules
    from app.core.clients.mongodb_client import get_mongodb_client
    from app.core.cache.redis_blacklist import RedisBlacklist
    from app.core.rate_limiter.rate_limiter import rate_limit
    
    # Or import DI from core (backward compatible)
    from app.core import DIContainer
    from app.core.di import init_di
"""

# Re-export from di/ for backward compatibility
from .di.di_container import DIContainer

# Other items should be imported directly from submodules
# to avoid circular imports and unnecessary loading

__all__ = [
    'DIContainer',
]
