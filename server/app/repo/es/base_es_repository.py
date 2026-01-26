"""
Base Elasticsearch Repository
==============================

Abstract base class for all ES repositories to avoid code duplication.
Provides common methods for index management, bulk operations, etc.

Author: Travel Agent P Team
Date: January 26, 2026
"""

import logging
import json
from pathlib import Path
from typing import Dict, Optional, Any
from abc import ABC, abstractmethod

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError, RequestError

from ...core.clients.elasticsearch_client import ElasticsearchClient

logger = logging.getLogger(__name__)


class BaseESRepository(ABC):
    """
    Base Elasticsearch Repository with common operations.
    
    Child classes must define:
    - INDEX_NAME: str
    - MAPPING_FILE: str (optional if override _load_mapping())
    """
    
    INDEX_NAME: str = None  # Override in child class
    MAPPING_FILE: str = None  # Override in child class
    
    def __init__(self, es_client: Optional[Elasticsearch] = None):
        """
        Initialize base ES repository.
        
        Args:
            es_client: Elasticsearch client (defaults to singleton)
        """
        if not self.INDEX_NAME:
            raise ValueError(f"{self.__class__.__name__} must define INDEX_NAME")
        
        self.es = es_client or ElasticsearchClient.get_instance()
        self.mapping = self._load_mapping()
        logger.info(f"Initialized {self.__class__.__name__} with index: {self.INDEX_NAME}")
    
    def _load_mapping(self) -> Dict:
        """
        Load index mapping from JSON file.
        
        Returns:
            Dict: Index mapping configuration
        """
        if not self.MAPPING_FILE:
            # Allow child classes to skip mapping file (e.g., dynamic mapping)
            logger.warning(f"{self.__class__.__name__} has no MAPPING_FILE defined")
            return {}
        
        try:
            mapping_path = Path(__file__).parent / "mappings" / self.MAPPING_FILE
            
            if not mapping_path.exists():
                logger.error(f"Mapping file not found: {mapping_path}")
                raise FileNotFoundError(f"Mapping file not found: {mapping_path}")
            
            with open(mapping_path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            
            logger.info(f"Loaded ES mapping from: {mapping_path}")
            return mapping
            
        except Exception as e:
            logger.error(f"Failed to load ES mapping: {e}")
            raise
    
    # =========================================================================
    # INDEX MANAGEMENT (Common methods)
    # =========================================================================
    
    def create_index(self, delete_if_exists: bool = False) -> bool:
        """
        Create index with mapping.
        
        Args:
            delete_if_exists: Delete existing index before creating
            
        Returns:
            True if created successfully
        """
        try:
            if self.es.indices.exists(index=self.INDEX_NAME):
                if delete_if_exists:
                    logger.warning(f"Deleting existing index: {self.INDEX_NAME}")
                    self.es.indices.delete(index=self.INDEX_NAME)
                else:
                    logger.info(f"Index {self.INDEX_NAME} already exists")
                    return True
            
            self.es.indices.create(index=self.INDEX_NAME, body=self.mapping)
            logger.info(f"Created index: {self.INDEX_NAME}")
            return True
            
        except RequestError as e:
            logger.error(f"Failed to create index {self.INDEX_NAME}: {e}")
            return False
    
    def delete_index(self) -> bool:
        """
        Delete index.
        
        Returns:
            True if deleted successfully
        """
        try:
            self.es.indices.delete(index=self.INDEX_NAME)
            logger.info(f"Deleted index: {self.INDEX_NAME}")
            return True
        except NotFoundError:
            logger.warning(f"Index {self.INDEX_NAME} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to delete index {self.INDEX_NAME}: {e}")
            return False
    
    def index_exists(self) -> bool:
        """
        Check if index exists.
        
        Returns:
            True if index exists
        """
        try:
            return self.es.indices.exists(index=self.INDEX_NAME)
        except Exception:
            return False
    
    def ensure_index(self) -> bool:
        """
        Ensure index exists, create if not.
        
        Returns:
            True if index exists or was created
        """
        if not self.index_exists():
            return self.create_index()
        return True
    
    def count(self) -> int:
        """
        Get total document count in index.
        
        Returns:
            Number of documents
        """
        try:
            result = self.es.count(index=self.INDEX_NAME)
            return result.get('count', 0)
        except NotFoundError:
            return 0
        except Exception as e:
            logger.error(f"Failed to count documents in {self.INDEX_NAME}: {e}")
            return 0
    
    def refresh_index(self) -> bool:
        """
        Refresh index to make recent changes searchable.
        
        Returns:
            True if refreshed successfully
        """
        try:
            self.es.indices.refresh(index=self.INDEX_NAME)
            return True
        except Exception as e:
            logger.error(f"Failed to refresh index {self.INDEX_NAME}: {e}")
            return False
    
    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        """
        Get document by ID.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Document dictionary or None if not found
        """
        try:
            response = self.es.get(index=self.INDEX_NAME, id=doc_id)
            return response['_source']
        except NotFoundError:
            logger.debug(f"Document not found in {self.INDEX_NAME}: {doc_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get document from {self.INDEX_NAME}: {e}")
            return None
    
    def delete_by_id(self, doc_id: str) -> bool:
        """
        Delete document by ID.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            self.es.delete(index=self.INDEX_NAME, id=doc_id)
            logger.info(f"Deleted document from {self.INDEX_NAME}: {doc_id}")
            return True
        except NotFoundError:
            logger.warning(f"Document not found for deletion in {self.INDEX_NAME}: {doc_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete document from {self.INDEX_NAME}: {e}")
            return False
    
    def index_document(self, doc: Dict, doc_id: Optional[str] = None) -> bool:
        """
        Index a single document.
        
        Args:
            doc: Document dictionary
            doc_id: Optional document ID (auto-generated if None)
            
        Returns:
            True if indexed successfully
        """
        try:
            self.es.index(index=self.INDEX_NAME, id=doc_id, document=doc)
            logger.debug(f"Indexed document in {self.INDEX_NAME}: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to index document in {self.INDEX_NAME}: {e}")
            return False
    
    # =========================================================================
    # ABSTRACT METHODS (Override in child classes for specific logic)
    # =========================================================================
    
    @abstractmethod
    def search(self, **kwargs) -> Dict[str, Any]:
        """
        Search documents. Must be implemented by child class.
        
        Returns:
            Dict with 'results', 'total', 'took_ms'
        """
        pass
