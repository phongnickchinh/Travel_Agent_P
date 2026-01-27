"""
Elasticsearch Initialization Module
====================================

Handles ES connection, index creation, and data synchronization from MongoDB.

Features:
- Create indexes with correct mappings (POI + Autocomplete)
- Sync POI data from MongoDB to ES
- Sync Autocomplete cache from MongoDB to ES
- Validate mappings for autocomplete support

Architecture:
    MongoDB ────sync────> Elasticsearch
      │                      │
      ├─ poi collection ────> pois index
      └─ autocomplete_cache ─> autocomplete index

Author: Travel Agent P Team
Date: December 24, 2025 (Refactored)
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class ESInitializer:
    """
    Elasticsearch Initializer - handles all ES setup logic.
    
    Centralizes:
    - ES connection check
    - Index creation
    - Data sync from MongoDB
    
    Usage:
        initializer = ESInitializer()
        initializer.initialize()  # Full initialization
        initializer.sync_autocomplete()  # Sync only autocomplete
    """
    
    def __init__(self):
        """Initialize with lazy imports to avoid circular dependencies."""
        self._es_client = None
        self._poi_repo = None
        self._autocomplete_repo = None
        self._plan_repo = None
        self._mongodb_client = None
    
    @property
    def es_client(self):
        """Lazy load ES client."""
        if self._es_client is None:
            from .clients.elasticsearch_client import ElasticsearchClient
            self._es_client = ElasticsearchClient.get_instance()
        return self._es_client
    
    @property
    def mongodb_client(self):
        """Lazy load MongoDB client."""
        if self._mongodb_client is None:
            from .clients.mongodb_client import get_mongodb_client
            self._mongodb_client = get_mongodb_client()
        return self._mongodb_client
    
    @property
    def poi_repo(self):
        """Lazy load POI ES repository."""
        if self._poi_repo is None:
            from ..repo.es.es_poi_repository import ESPOIRepository
            self._poi_repo = ESPOIRepository(self.es_client)
        return self._poi_repo
    
    @property
    def autocomplete_repo(self):
        """Lazy load Autocomplete ES repository."""
        if self._autocomplete_repo is None:
            from ..repo.es.es_autocomplete_repository import ESAutocompleteRepository
            self._autocomplete_repo = ESAutocompleteRepository(self.es_client)
        return self._autocomplete_repo
    
    @property
    def plan_repo(self):
        """Lazy load Plan ES repository."""
        if self._plan_repo is None:
            from ..repo.es.es_plan_repository import ESPlanRepository
            self._plan_repo = ESPlanRepository(self.es_client)
        return self._plan_repo
    
    def is_connected(self) -> bool:
        """Check if ES is connected."""
        try:
            return self.es_client.ping()
        except Exception:
            return False
    
    def initialize(self, skip_sync: bool = True) -> bool:
        """
        Elasticsearch initialization.
        
        1. Check ES connection
        2. Create indexes (POI + Autocomplete + Plan)
        3. Skip sync by default (Celery worker handles sync on startup)
        
        Args:
            skip_sync: If True (default), only create indexes - Celery handles sync
                      If False, also run sync (for manual/testing purposes)
        
        Returns:
            True if initialization successful
        """
        try:
            # Check connection with timeout
            if not self.is_connected():
                logger.warning("[ES_INIT] Elasticsearch connection failed")
                return False
            
            logger.info("[ES_INIT] Elasticsearch connected successfully")
            
            # Create/verify indexes (fast, do synchronously)
            self._ensure_poi_index()
            self._ensure_autocomplete_index()
            self._ensure_plan_index()
            
            if skip_sync:
                logger.info("[ES_INIT] Indexes verified. Sync will be handled by Celery worker.")
            else:
                logger.info("[ES_INIT] Running sync...")
                self._run_sync()
            
            return True
            
        except Exception as e:
            logger.error("[ES_INIT] Initialization failed: %s", e)
            return False
    
    def _run_sync(self):
        """Run all sync operations synchronously."""
        try:
            self.sync_pois()
            self.sync_autocomplete()
            self.sync_plans()
            self._validate_mappings()
            logger.info("[ES_INIT] All sync operations completed")
        except Exception as e:
            logger.error("[ES_INIT] Sync failed: %s", e)
    
    def _ensure_poi_index(self) -> bool:
        """Ensure POI index exists with correct mapping."""
        try:
            index_name = self.poi_repo.INDEX_NAME
            
            if not self.es_client.indices.exists(index=index_name):
                logger.info(f"[ES_INIT] Creating POI index: {index_name}")
                if self.poi_repo.create_index():
                    logger.info(f"[ES_INIT] POI index '{index_name}' created successfully")
                    return True
                else:
                    logger.error(f"[ES_INIT] Failed to create POI index")
                    return False
            else:
                logger.info(f"[ES_INIT] POI index '{index_name}' already exists")
                return False
                
        except Exception as e:
            logger.error(f"[ES_INIT] POI index error: {e}")
            return False
    
    def _ensure_autocomplete_index(self) -> bool:
        """Ensure Autocomplete index exists with correct mapping."""
        try:
            index_name = self.autocomplete_repo.INDEX_NAME
            
            if not self.es_client.indices.exists(index=index_name):
                logger.info(f"[ES_INIT] Creating Autocomplete index: {index_name}")
                if self.autocomplete_repo.create_index():
                    logger.info(f"[ES_INIT] Autocomplete index '{index_name}' created successfully")
                    return True
                else:
                    logger.error(f"[ES_INIT] Failed to create Autocomplete index")
                    return False
            else:
                logger.info(f"[ES_INIT] Autocomplete index '{index_name}' already exists")
                return False
                
        except Exception as e:
            logger.error(f"[ES_INIT] Autocomplete index error: {e}")
            return False
    
    def _ensure_plan_index(self) -> bool:
        """Ensure Plan index exists with correct mapping."""
        try:
            index_name = self.plan_repo.INDEX_NAME
            
            if not self.es_client.indices.exists(index=index_name):
                logger.info(f"[ES_INIT] Creating Plan index: {index_name}")
                if self.plan_repo.create_index():
                    logger.info(f"[ES_INIT] Plan index '{index_name}' created successfully")
                    return True
                else:
                    logger.error(f"[ES_INIT] Failed to create Plan index")
                    return False
            else:
                logger.info(f"[ES_INIT] Plan index '{index_name}' already exists")
                return False
                
        except Exception as e:
            logger.error(f"[ES_INIT] Plan index error: {e}")
            return False
    
    def sync_pois(self, batch_size: int = 100) -> Tuple[int, int]:
        """
        Sync all POIs from MongoDB to Elasticsearch.
        
        Will skip if ES already has >= MongoDB count (already synced).
        
        Args:
            batch_size: Number of POIs to index per batch
            
        Returns:
            Tuple of (indexed_count, failed_count)
        """
        try:
            poi_collection = self.mongodb_client.get_collection('poi')
            if poi_collection is None:
                logger.warning("[ES_INIT] POI collection not available")
                return (0, 0)
            
            total_pois = poi_collection.count_documents({})
            logger.info(f"[ES_INIT] Starting POI sync: {total_pois} documents in MongoDB")
            
            if total_pois == 0:
                logger.info("[ES_INIT] No POIs found in MongoDB to sync")
                return (0, 0)
            
            # Check ES count first - skip if already synced
            try:
                es_count = self.poi_repo.count()
                if es_count >= total_pois:
                    logger.info(f"[ES_INIT] POI ES already synced ({es_count} items, MongoDB has {total_pois})")
                    return (es_count, 0)
                else:
                    logger.info(f"[ES_INIT] POI ES has {es_count} items, MongoDB has {total_pois} - syncing {total_pois - es_count} new items")
            except Exception as e:
                logger.warning(f"[ES_INIT] Could not get ES count, proceeding with full sync: {e}")
            
            batch = []
            indexed_count = 0
            failed_count = 0
            
            cursor = poi_collection.find().batch_size(batch_size)
            
            for poi in cursor:
                # Remove MongoDB _id
                if '_id' in poi:
                    poi['_id'] = str(poi['_id'])
                batch.append(poi)
                
                if len(batch) >= batch_size:
                    success, failed = self.poi_repo.bulk_index(batch)
                    indexed_count += success
                    failed_count += failed
                    batch = []
                    logger.debug(f"[ES_INIT] POI sync progress: {indexed_count}/{total_pois}")
            
            # Index remaining POIs
            if batch:
                success, failed = self.poi_repo.bulk_index(batch)
                indexed_count += success
                failed_count += failed
            
            logger.info(f"[ES_INIT] POI sync completed: {indexed_count} indexed, {failed_count} failed")
            return (indexed_count, failed_count)
            
        except Exception as e:
            logger.error(f"[ES_INIT] POI sync error: {e}")
            return (0, 0)
    
    def sync_autocomplete(self, batch_size: int = 100) -> Tuple[int, int]:
        """
        Sync all Autocomplete cache from MongoDB to Elasticsearch.
        
        Args:
            batch_size: Number of items to index per batch
            
        Returns:
            Tuple of (indexed_count, failed_count)
        """
        try:
            autocomplete_collection = self.mongodb_client.get_collection('autocomplete_cache')
            if autocomplete_collection is None:
                logger.warning("[ES_INIT] Autocomplete collection not available")
                return (0, 0)
            
            total_items = autocomplete_collection.count_documents({})
            logger.info(f"[ES_INIT] Starting Autocomplete sync: {total_items} documents in MongoDB")
            
            if total_items == 0:
                logger.info("[ES_INIT] No Autocomplete items found in MongoDB to sync")
                return (0, 0)
            
            # Check ES count first
            es_count = self.autocomplete_repo.count()
            if es_count >= total_items:
                logger.info(f"[ES_INIT] Autocomplete ES already synced ({es_count} items)")
                return (es_count, 0)
            
            batch = []
            indexed_count = 0
            failed_count = 0
            
            cursor = autocomplete_collection.find().batch_size(batch_size)
            
            for item in cursor:
                # Remove MongoDB _id and convert
                if '_id' in item:
                    del item['_id']
                
                batch.append(item)
                
                if len(batch) >= batch_size:
                    success, failed = self.autocomplete_repo.bulk_index(batch)
                    indexed_count += success
                    failed_count += failed
                    batch = []
                    logger.debug(f"[ES_INIT] Autocomplete sync progress: {indexed_count}/{total_items}")
            
            # Index remaining items
            if batch:
                success, failed = self.autocomplete_repo.bulk_index(batch)
                indexed_count += success
                failed_count += failed
            
            logger.info(f"[ES_INIT] Autocomplete sync completed: {indexed_count} indexed, {failed_count} failed")
            return (indexed_count, failed_count)
            
        except Exception as e:
            logger.error(f"[ES_INIT] Autocomplete sync error: {e}")
            return (0, 0)
    
    def sync_plans(self, batch_size: int = 100) -> Tuple[int, int]:
        """
        Sync all Plans from MongoDB to Elasticsearch.
        
        Args:
            batch_size: Number of items to index per batch
        Returns:
            Tuple of (indexed_count, failed_count)
        """
        try:
            plan_collection = self.mongodb_client.get_collection('plan')
            if plan_collection is None:
                logger.warning("[ES_INIT] Plans collection not available")
                return (0, 0)
            
            total_plans = plan_collection.count_documents({'status': 'completed', 'is_deleted': {'$ne': True}})
            logger.info(f"[ES_INIT] Starting Plan sync: {total_plans} completed plans in MongoDB")
            
            if total_plans == 0:
                logger.info("[ES_INIT] No completed plans found in MongoDB to sync")
                return (0, 0)
            
            try:
                es_count = self.plan_repo.count()
                if es_count >= total_plans:
                    logger.info(f"[ES_INIT] Plan ES already synced ({es_count} items)")
                    return (es_count, 0)
            except Exception as e:
                logger.warning(f"[ES_INIT] Could not get ES plan count: {e}")
            
            indexed_count = 0
            failed_count = 0
            
            cursor = plan_collection.find({'status': 'completed', 'is_deleted': {'$ne': True}}).batch_size(batch_size)
            
            for plan in cursor:
                try:
                    doc = {
                        'plan_id': plan.get('plan_id'),
                        'user_id': plan.get('user_id'),
                        'destination': plan.get('destination', ''),
                        'title': plan.get('title', '')
                    }
                    if doc['plan_id'] and doc['user_id']:
                        self.plan_repo.index_document(doc, doc['plan_id'])
                        indexed_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.debug(f"[ES_INIT] Failed to index plan: {e}")
            
            logger.info(f"[ES_INIT] Plan sync completed: {indexed_count} indexed, {failed_count} failed")
            return (indexed_count, failed_count)
            
        except Exception as e:
            logger.error(f"[ES_INIT] Plan sync error: {e}")
            return (0, 0)
    
    def _validate_mappings(self):
        """Validate ES mappings have required fields."""
        try:
            # Validate POI mapping
            poi_index = self.poi_repo.INDEX_NAME
            if self.es_client.indices.exists(index=poi_index):
                mapping = self.es_client.indices.get_mapping(index=poi_index)
                properties = mapping[poi_index].get('mappings', {}).get('properties', {})
                name_mapping = properties.get('name', {})
                has_edge_ngram = 'edge_ngram' in name_mapping.get('fields', {})
                
                if has_edge_ngram:
                    logger.info(f"[ES_INIT] POI mapping verified (edge_ngram present)")
                else:
                    logger.warning(f"[ES_INIT] POI mapping missing edge_ngram field")
            
            # Validate Autocomplete mapping
            auto_index = self.autocomplete_repo.INDEX_NAME
            if self.es_client.indices.exists(index=auto_index):
                mapping = self.es_client.indices.get_mapping(index=auto_index)
                properties = mapping[auto_index].get('mappings', {}).get('properties', {})
                
                # Check required fields
                required = ['place_id', 'main_text', 'description', 'types']
                missing = [f for f in required if f not in properties]
                
                if missing:
                    logger.warning(f"[ES_INIT] Autocomplete mapping missing fields: {missing}")
                else:
                    logger.info(f"[ES_INIT] Autocomplete mapping verified")
                    
        except Exception as e:
            logger.warning(f"[ES_INIT] Mapping validation error: {e}")


# Singleton instance
_initializer: Optional[ESInitializer] = None


def get_es_initializer() -> ESInitializer:
    """Get or create ESInitializer singleton."""
    global _initializer
    if _initializer is None:
        _initializer = ESInitializer()
    return _initializer


def initialize_elasticsearch() -> bool:
    """
    Initialize Elasticsearch (called from create_app).
    
    Returns:
        True if initialization successful
    """
    initializer = get_es_initializer()
    return initializer.initialize()


def sync_autocomplete_to_es() -> Tuple[int, int]:
    """
    Sync Autocomplete data from MongoDB to ES.
    
    Can be called manually or from a scheduled job.
    
    Returns:
        Tuple of (indexed_count, failed_count)
    """
    initializer = get_es_initializer()
    return initializer.sync_autocomplete()
