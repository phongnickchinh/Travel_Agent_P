"""
MongoDB Client - Singleton Pattern
===================================

Purpose:
- Provides a single MongoDB connection instance across the application
- Handles connection pooling and error handling
- Similar pattern to RedisClient for consistency

Usage:
    from app.core.mongodb_client import get_mongodb_client
    
    db = get_mongodb_client()
    poi_collection = db["poi"]
    result = poi_collection.find_one({"poi_id": "poi_123"})

Author: Travel Agent P Team
Date: October 27, 2025
"""

import os
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import (
    ConnectionFailure,
    ServerSelectionTimeoutError,
    ConfigurationError
)
import logging

logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    Singleton MongoDB client for application-wide use.
    
    Features:
    - Connection pooling (configurable via env vars)
    - Automatic reconnection on failure
    - Health checking
    - Graceful degradation
    """
    
    _instance: Optional['MongoDBClient'] = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None
    
    def __new__(cls):
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize MongoDB client on first instantiation."""
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """
        Establish MongoDB connection with configuration from environment.
        
        Environment Variables:
        - MONGODB_URI: Full connection string (e.g., mongodb://localhost:27017/travel_agent_poi)
        - MONGODB_DB_NAME: Database name (fallback if not in URI)
        - MONGODB_MAX_POOL_SIZE: Max connections in pool (default: 50)
        - MONGODB_MIN_POOL_SIZE: Min connections in pool (default: 10)
        - MONGODB_SERVER_SELECTION_TIMEOUT_MS: Server selection timeout (default: 5000)
        - MONGODB_CONNECT_TIMEOUT_MS: Connection timeout (default: 10000)
        """
        try:
            # Get configuration from environment
            mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/travel_agent_poi')
            db_name = os.getenv('MONGODB_DB_NAME', 'travel_agent_poi')
            
            # Connection pool settings
            max_pool_size = int(os.getenv('MONGODB_MAX_POOL_SIZE', '50'))
            min_pool_size = int(os.getenv('MONGODB_MIN_POOL_SIZE', '10'))
            server_selection_timeout_ms = int(os.getenv('MONGODB_SERVER_SELECTION_TIMEOUT_MS', '5000'))
            connect_timeout_ms = int(os.getenv('MONGODB_CONNECT_TIMEOUT_MS', '10000'))
            
            # Mask sensitive connection string for logging
            masked_uri = mongodb_uri.split('@')[-1] if '@' in mongodb_uri else 'localhost:27017'
            logger.info(f"🔗 Connecting to MongoDB: mongodb+srv://***:***@{masked_uri}")
            
            # Create MongoDB client
            self._client = MongoClient(
                mongodb_uri,
                maxPoolSize=max_pool_size,
                minPoolSize=min_pool_size,
                serverSelectionTimeoutMS=server_selection_timeout_ms,
                connectTimeoutMS=connect_timeout_ms,
                retryWrites=True,  # Automatic retry for write operations
                retryReads=True    # Automatic retry for read operations
            )
            
            # Get database instance
            self._db = self._client[db_name]
            
            # Test connection
            self._client.admin.command('ping')
            
            logger.info(f"✅ MongoDB connected successfully to database: {db_name}")
            logger.info(f"📊 Connection pool: min={min_pool_size}, max={max_pool_size}")
            
        except ConnectionFailure as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            self._client = None
            self._db = None
            raise
        
        except ServerSelectionTimeoutError as e:
            logger.error(f"❌ MongoDB server selection timeout: {e}")
            logger.error("   Check if MongoDB is running and accessible")
            self._client = None
            self._db = None
            raise
        
        except ConfigurationError as e:
            logger.error(f"❌ MongoDB configuration error: {e}")
            self._client = None
            self._db = None
            raise
        
        except Exception as e:
            logger.error(f"❌ Unexpected MongoDB error: {e}")
            self._client = None
            self._db = None
            raise
    
    def get_database(self) -> Optional[Database]:
        """
        Get MongoDB database instance.
        
        Returns:
            Database instance if connected, None otherwise
            
        Example:
            db = mongodb_client.get_database()
            if db:
                poi = db["poi"].find_one({"poi_id": "poi_123"})
        """
        if self._db is None:
            logger.warning("⚠️ MongoDB database not available, attempting reconnect...")
            try:
                self._connect()
            except Exception as e:
                logger.error(f"❌ Reconnection failed: {e}")
                return None
        
        return self._db
    
    def get_client(self) -> Optional[MongoClient]:
        """
        Get raw MongoDB client instance (for advanced operations).
        
        Returns:
            MongoClient instance if connected, None otherwise
        """
        if self._client is None:
            logger.warning("⚠️ MongoDB client not available, attempting reconnect...")
            try:
                self._connect()
            except Exception as e:
                logger.error(f"❌ Reconnection failed: {e}")
                return None
        
        return self._client
    
    def is_healthy(self) -> bool:
        """
        Check if MongoDB connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
            
        Example:
            if mongodb_client.is_healthy():
                # Proceed with database operations
            else:
                # Use fallback or return error
        """
        if self._client is None or self._db is None:
            return False
        
        try:
            # Ping the server
            self._client.admin.command('ping')
            return True
        except Exception as e:
            logger.warning(f"⚠️ MongoDB health check failed: {e}")
            return False
    
    def close(self):
        """
        Close MongoDB connection.
        
        Should be called on application shutdown.
        
        Example:
            # In app shutdown handler
            mongodb_client.close()
        """
        if self._client:
            logger.info("🔌 Closing MongoDB connection...")
            self._client.close()
            self._client = None
            self._db = None
            logger.info("✅ MongoDB connection closed")
    
    def get_collection(self, collection_name: str):
        """
        Get a specific collection from the database.
        
        Args:
            collection_name: Name of the collection (e.g., "poi", "itineraries")
        
        Returns:
            Collection instance if connected, None otherwise
            
        Example:
            poi_collection = mongodb_client.get_collection("poi")
            if poi_collection:
                result = poi_collection.find_one({"poi_id": "poi_123"})
        """
        db = self.get_database()
        if db is None:
            return None
        
        return db[collection_name]
    
    def create_indexes(self):
        """
        Create indexes for all collections.
        
        Should be called during application initialization.
        Indexes improve query performance significantly.
        
        Collections:
        - poi: dedupe_key (unique), location (2dsphere), categories, text search
        - itineraries: user_id, plan_id (unique), created_at
        - reviews: user_id, poi_id, created_at
        """
        try:
            db = self.get_database()
            if db is None:
                logger.error("❌ Cannot create indexes: Database not available")
                return
            
            logger.info("🔨 Creating MongoDB indexes...")
            
            # POI Collection Indexes
            poi_collection = db["poi"]
            
            # Unique deduplication key
            poi_collection.create_index("dedupe_key", unique=True, name="idx_dedupe_key")
            logger.info("✅ Created unique index: poi.dedupe_key")
            
            # GeoJSON 2dsphere for location queries
            poi_collection.create_index([("location", "2dsphere")], name="idx_location_2dsphere")
            logger.info("✅ Created 2dsphere index: poi.location")
            
            # Category filter
            poi_collection.create_index("categories", name="idx_categories")
            logger.info("✅ Created index: poi.categories")
            
            # Text search (fallback if no Elasticsearch)
            poi_collection.create_index(
                [
                    ("name", "text"),
                    ("name_unaccented", "text"),
                    ("description.short", "text")
                ],
                name="idx_text_search",
                default_language="english"
            )
            logger.info("✅ Created text search index: poi.name/description")
            
            # Popularity & sorting
            poi_collection.create_index([("metadata.popularity_score", -1)], name="idx_popularity")
            poi_collection.create_index([("ratings.average", -1)], name="idx_ratings")
            logger.info("✅ Created sorting indexes: poi.popularity/ratings")
            
            # POI ID for fast lookups
            poi_collection.create_index("poi_id", unique=True, name="idx_poi_id")
            logger.info("✅ Created unique index: poi.poi_id")
            
            # Itinerary Collection Indexes
            itinerary_collection = db["itineraries"]
            
            # Plan ID (unique)
            itinerary_collection.create_index("plan_id", unique=True, name="idx_plan_id")
            logger.info("✅ Created unique index: itineraries.plan_id")
            
            # User's itineraries
            itinerary_collection.create_index("metadata.user_id", name="idx_user_id")
            logger.info("✅ Created index: itineraries.user_id")
            
            # Created date for sorting
            itinerary_collection.create_index([("metadata.created_at", -1)], name="idx_created_at")
            logger.info("✅ Created index: itineraries.created_at")
            
            # Public itineraries
            itinerary_collection.create_index("metadata.is_public", name="idx_is_public")
            logger.info("✅ Created index: itineraries.is_public")
            
            # Share token lookup
            itinerary_collection.create_index("metadata.share_token", sparse=True, name="idx_share_token")
            logger.info("✅ Created sparse index: itineraries.share_token")
            
            # Review Collection Indexes (Future)
            review_collection = db["reviews"]
            
            # User's reviews
            review_collection.create_index("user_id", name="idx_review_user_id")
            logger.info("✅ Created index: reviews.user_id")
            
            # POI's reviews
            review_collection.create_index("poi_id", name="idx_review_poi_id")
            logger.info("✅ Created index: reviews.poi_id")
            
            # Created date
            review_collection.create_index([("created_at", -1)], name="idx_review_created_at")
            logger.info("✅ Created index: reviews.created_at")
            
            logger.info("🎉 All MongoDB indexes created successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
            raise


# Singleton instance
_mongodb_client_instance: Optional[MongoDBClient] = None


def get_mongodb_client() -> MongoDBClient:
    """
    Get the singleton MongoDB client instance.
    
    Returns:
        MongoDBClient instance
        
    Example:
        from app.core.mongodb_client import get_mongodb_client
        
        client = get_mongodb_client()
        db = client.get_database()
        poi = db["poi"].find_one({"poi_id": "poi_123"})
    """
    global _mongodb_client_instance
    
    if _mongodb_client_instance is None:
        _mongodb_client_instance = MongoDBClient()
    
    return _mongodb_client_instance


def get_mongodb_database() -> Optional[Database]:
    """
    Convenience function to get database directly.
    
    Returns:
        Database instance if connected, None otherwise
        
    Example:
        from app.core.mongodb_client import get_mongodb_database
        
        db = get_mongodb_database()
        if db:
            poi = db["poi"].find_one({"poi_id": "poi_123"})
    """
    client = get_mongodb_client()
    return client.get_database()


def close_mongodb_connection():
    """
    Close MongoDB connection on application shutdown.
    
    Should be called in Flask app teardown handler.
    
    Example:
        @app.teardown_appcontext
        def shutdown_session(exception=None):
            close_mongodb_connection()
    """
    global _mongodb_client_instance
    
    if _mongodb_client_instance:
        _mongodb_client_instance.close()
        _mongodb_client_instance = None
