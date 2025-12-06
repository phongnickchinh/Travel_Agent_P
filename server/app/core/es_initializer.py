"""
Elasticsearch Initialization Module
Handles ES index creation and POI synchronization from MongoDB
"""

import logging

logger = logging.getLogger(__name__)


def initialize_elasticsearch():
    """
    Initialize Elasticsearch index and sync POIs from MongoDB
    
    - Checks if ES index exists
    - Creates index with correct mapping if missing
    - Syncs POIs from MongoDB to ES
    - Validates mapping for autocomplete support
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    from .elasticsearch_client import ElasticsearchClient
    from .mongodb_client import get_mongodb_client
    from ..repo.es.es_poi_repository import ESPOIRepository
    
    try:
        es_client = ElasticsearchClient.get_instance()
        if not es_client.ping():
            print("[INIT] WARNING: Elasticsearch connection failed")
            return False
        
        print("[INIT] Elasticsearch connected successfully")
        
        es_repo = ESPOIRepository(es_client)
        
        # Check if index exists
        if not es_client.indices.exists(index=es_repo.INDEX_NAME):
            print(f"[INIT] Elasticsearch index '{es_repo.INDEX_NAME}' not found. Creating...")
            
            # Create index with correct mapping
            if es_repo.create_index():
                print(f"[INIT] Elasticsearch index '{es_repo.INDEX_NAME}' created successfully")
                _sync_pois_from_mongodb(es_repo)
                
            else:
                print("[INIT] Failed to create Elasticsearch index")
                return False
        else:
            print(f"[INIT] Elasticsearch index '{es_repo.INDEX_NAME}' already exists")
            _sync_pois_from_mongodb(es_repo)
            
            # Verify mapping has edge_ngram for autocomplete
            _validate_es_mapping(es_client, es_repo.INDEX_NAME)
        
        return True
    
    except Exception as es_error:
        print(f"[INIT] WARNING: Elasticsearch initialization failed: {str(es_error)}")
        print("[INIT] WARNING: Search and autocomplete features will not be available")
        logger.exception("Elasticsearch initialization error")
        return False


def _sync_pois_from_mongodb(es_repo):
    """
    Sync all POIs from MongoDB to Elasticsearch
    
    Args:
        es_repo: ESPOIRepository instance
    """
    from .mongodb_client import get_mongodb_client
    
    try:
        mongodb_client = get_mongodb_client()
        poi_collection = mongodb_client.get_collection('poi')
        
        total_pois = poi_collection.count_documents({})
        print(f"[INIT] Starting POI sync: {total_pois} documents found in MongoDB")
        
        if total_pois == 0:
            print("[INIT] No POIs found in MongoDB to sync")
            return
        
        batch_size = 100
        batch = []
        indexed_count = 0
        failed_count = 0
        
        cursor = poi_collection.find().batch_size(batch_size)
        
        for poi in cursor:
            batch.append(poi)
            
            if len(batch) >= batch_size:
                success, failed = es_repo.bulk_index(batch)
                indexed_count += success
                failed_count += failed
                batch = []
                print(f"[INIT] Synced {indexed_count}/{total_pois} POIs...")
        
        # Index remaining POIs
        if batch:
            success, failed = es_repo.bulk_index(batch)
            indexed_count += success
            failed_count += failed
        
        print(f"[INIT] POI sync completed: {indexed_count} indexed, {failed_count} failed")
    
    except Exception as sync_error:
        print(f"[INIT] POI sync failed: {str(sync_error)}")
        print("[INIT] Elasticsearch index created but empty - sync manually if needed")
        logger.exception("POI sync error")


def _validate_es_mapping(es_client, index_name):
    """
    Validate that ES mapping has required fields for autocomplete
    
    Args:
        es_client: Elasticsearch client instance
        index_name: Name of the index to validate
    """
    try:
        mapping = es_client.indices.get_mapping(index=index_name)
        name_mapping = mapping[index_name]['mappings']['properties'].get('name', {})
        has_edge_ngram = 'edge_ngram' in name_mapping.get('fields', {})
        
        if not has_edge_ngram:
            print("[INIT] WARNING: Elasticsearch mapping is missing 'edge_ngram' field")
            print("[INIT] WARNING: Autocomplete may not work correctly")
            print("[INIT] WARNING: Run 'python scripts/fix_es_mapping.py' to fix this")
        else:
            print("[INIT] Elasticsearch mapping verified (edge_ngram present)")
    
    except Exception as mapping_check_error:
        print(f"[INIT] Could not verify ES mapping: {str(mapping_check_error)}")
        logger.exception("ES mapping validation error")
