"""
Database Clients Module
=======================

Provides singleton client connections for:
- MongoDB (document store for POIs, Plans)
- Redis (caching, rate limiting, blacklist)
- Elasticsearch (full-text search)
"""

from .mongodb_client import MongoDBClient, get_mongodb_client
from .redis_client import RedisClient, get_redis
from .elasticsearch_client import ElasticsearchClient

__all__ = [
    'MongoDBClient',
    'get_mongodb_client',
    'RedisClient', 
    'get_redis',
    'ElasticsearchClient'
]
