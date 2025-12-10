"""
Elasticsearch Client Singleton
Manages connection to Elasticsearch cluster
"""

import os
import logging
from typing import Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, AuthenticationException

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """
    Singleton Elasticsearch client
    
    Manages connection to ES cluster with:
    - Connection pooling
    - Authentication
    - Retry logic
    - Health checks
    
    Usage:
        # Get ES client instance
        es = ElasticsearchClient.get_instance()
        
        # Use it
        es.index(index='pois', document={...})
        
        # Check health
        if ElasticsearchClient.is_healthy():
            # Perform ES operations
    """
    
    _instance: Optional[Elasticsearch] = None
    _is_initialized: bool = False
    
    @classmethod
    def get_instance(cls) -> Elasticsearch:
        """
        Get or create Elasticsearch client instance
        
        Returns:
            Elasticsearch client instance
            
        Raises:
            ValueError: If configuration is missing
            ConnectionError: If cannot connect to ES
        """
        if cls._instance is None:
            cls._instance = cls._create_client()
            cls._is_initialized = True
        
        return cls._instance
    
    @classmethod
    def _create_client(cls) -> Elasticsearch:
        """
        Create new Elasticsearch client with configuration from environment
        
        Returns:
            Configured Elasticsearch client
        """
        # Get configuration from environment
        deploy_type = os.getenv('ELASTICSEARCH_DEPLOY_TYPE', 'docker').lower()
        es_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
        api_key = os.getenv('ELASTICSEARCH_API_KEY')
        cloud_api_key = os.getenv('ELASTICSEARCH_CLOUD_API_KEY')
        username = os.getenv('ELASTICSEARCH_USERNAME')
        password = os.getenv('ELASTICSEARCH_PASSWORD')
        cloud_id = os.getenv('ELASTICSEARCH_CLOUD_ID')
        verify_certs = os.getenv('ELASTICSEARCH_VERIFY_CERTS', 'true').lower() == 'true'
        
        # Build client configuration
        client_config = {
            'request_timeout': 30,
            'max_retries': 3,
            'retry_on_timeout': True,
            'verify_certs': verify_certs,
        }
        
        # Authentication methods based on deployment type
        logger.info(f"Elasticsearch type: {deploy_type}")
        if deploy_type == 'cloud' and cloud_id:
            # Elastic Cloud
            client_config['cloud_id'] = cloud_id
            
            if cloud_api_key:
                client_config['api_key'] = cloud_api_key
            elif api_key:
                client_config['api_key'] = api_key
            elif username and password:
                client_config['basic_auth'] = (username, password)
            else:
                logger.warning("Elastic Cloud ID provided but no authentication credentials")
            
            logger.info(f"Connecting to Elastic Cloud: {cloud_id[:20]}...")
            
        else:
            # Docker / Self-hosted ES
            client_config['hosts'] = [es_url]
            
            if api_key:
                client_config['api_key'] = api_key
                logger.info(f"Using API key authentication for ES: {es_url}")
            elif username and password:
                client_config['basic_auth'] = (username, password)
                logger.info(f"Using basic authentication for ES: {es_url}")
            else:
                logger.info(f"Connecting to ES without authentication: {es_url}")
        
        try:
            # Create client
            client = Elasticsearch(**client_config)
            
            # Test connection
            if client.ping():
                info = client.info()
                version = info.get('version', {}).get('number', 'unknown')
                cluster_name = info.get('cluster_name', 'unknown')
                
                logger.info(f"[ELASTICSEARCH] Connected to Elasticsearch cluster '{cluster_name}' (version {version})")
                return client
            else:
                raise ConnectionError("Failed to ping Elasticsearch cluster")
                
        except AuthenticationException as e:
            logger.error(f"[ELASTICSEARCH] Authentication failed: {e}")
            raise
        except ConnectionError as e:
            logger.error(f"[ELASTICSEARCH] Cannot connect to Elasticsearch: {e}")
            raise
        except Exception as e:
            logger.error(f"[ELASTICSEARCH] Unexpected error connecting to Elasticsearch: {e}")
            raise
    
    @classmethod
    def is_healthy(cls) -> bool:
        """
        Check if Elasticsearch cluster is healthy
        
        Returns:
            True if cluster is reachable and healthy
        """
        try:
            if cls._instance is None:
                return False
            
            return cls._instance.ping()
        except Exception as e:
            logger.warning(f"Elasticsearch health check failed: {e}")
            return False
    
    @classmethod
    def get_cluster_health(cls) -> dict:
        """
        Get detailed cluster health information
        
        Returns:
            Cluster health dictionary
        """
        try:
            es = cls.get_instance()
            health = es.cluster.health()
            return health
        except Exception as e:
            logger.error(f"Failed to get cluster health: {e}")
            return {
                'status': 'unavailable',
                'error': str(e)
            }
    
    @classmethod
    def reset(cls):
        """
        Reset client instance (for testing or reconnection)
        """
        if cls._instance:
            try:
                cls._instance.close()
            except Exception as e:
                logger.warning(f"Error closing ES client: {e}")
        
        cls._instance = None
        cls._is_initialized = False
        logger.info("Elasticsearch client reset")
    
    @classmethod
    def close(cls):
        """
        Close Elasticsearch connection
        """
        cls.reset()
