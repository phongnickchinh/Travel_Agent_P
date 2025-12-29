"""
Elasticsearch Autocomplete Cache Repository
============================================

Purpose:
- Manage autocomplete_cache index in Elasticsearch
- Provide fast autocomplete search with edge n-gram
- Support geo-distance boosting and popularity boosting
- Sync with MongoDB autocomplete_cache collection

Author: Travel Agent P Team
Date: December 22, 2025
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch.exceptions import NotFoundError, RequestError

from ...core.clients.elasticsearch_client import ElasticsearchClient
from ...model.mongo.autocomplete_cache import AutocompleteItem, CacheStatus
from .interfaces import ESAutocompleteRepositoryInterface

logger = logging.getLogger(__name__)


class ESAutocompleteRepository(ESAutocompleteRepositoryInterface):
    """
    Elasticsearch repository for autocomplete cache.
    
    Features:
    - Edge n-gram autocomplete search
    - Popularity boosting (click_count)
    - Geo-distance boosting (optional)
    - Type filtering (locality, neighborhood, etc.)
    - Bulk indexing for sync from MongoDB
    
    Index: autocomplete_cache
    Mapping: repo/es/mappings/autocomplete_cache_mapping.json
    
    Usage:
        repo = ESAutocompleteRepository()
        
        # Create index
        repo.create_index()
        
        # Search autocomplete
        results = repo.search("paris", limit=10)
        
        # Index item from Google API
        repo.index_item(autocomplete_item.to_es_document())
    """
    
    INDEX_NAME = "autocomplete"
    MAPPING_FILE = "autocomplete_cache_mapping.json"
    
    def __init__(self, es_client: Optional[Elasticsearch] = None):
        """
        Initialize ES Autocomplete Repository.
        
        Args:
            es_client: Elasticsearch client (defaults to singleton)
        """
        self.es = es_client or ElasticsearchClient.get_instance()
        self.mapping = self._load_mapping()
        logger.info(f"Initialized ESAutocompleteRepository with index: {self.INDEX_NAME}")
    
    def _load_mapping(self) -> Dict:
        """Load index mapping from JSON file."""
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
    # INDEX MANAGEMENT
    # =========================================================================
    
    def create_index(self, delete_if_exists: bool = False) -> bool:
        """
        Create autocomplete_cache index with mapping.
        
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
            logger.error(f"Failed to create index: {e}")
            return False
    
    def delete_index(self) -> bool:
        """Delete autocomplete_cache index."""
        try:
            self.es.indices.delete(index=self.INDEX_NAME)
            logger.info(f"Deleted index: {self.INDEX_NAME}")
            return True
        except NotFoundError:
            logger.warning(f"Index {self.INDEX_NAME} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            return False
    
    def index_exists(self) -> bool:
        """Check if index exists."""
        try:
            return self.es.indices.exists(index=self.INDEX_NAME)
        except Exception:
            return False
    
    def ensure_index(self) -> bool:
        """Ensure index exists, create if not."""
        if not self.index_exists():
            return self.create_index()
        return True
    
    def count(self) -> int:
        """Count total documents in index."""
        try:
            result = self.es.count(index=self.INDEX_NAME)
            return result.get('count', 0)
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            return 0
    
    # =========================================================================
    # INDEXING
    # =========================================================================
    
    def index_item(self, item: Dict[str, Any]) -> bool:
        """
        Index a single autocomplete item.
        
        Args:
            item: Dictionary with autocomplete data (from AutocompleteItem.to_es_document())
            
        Returns:
            True if indexed successfully
        """
        try:
            place_id = item.get('place_id')
            if not place_id:
                logger.error("Cannot index item without place_id")
                return False
            
            # Ensure updated_at is current
            item['updated_at'] = datetime.utcnow().isoformat()
            
            self.es.index(
                index=self.INDEX_NAME,
                id=place_id,
                document=item
            )
            
            logger.debug(f"Indexed autocomplete item: {item.get('main_text', 'Unknown')} ({place_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index autocomplete item: {e}")
            return False
    
    def index_from_model(self, item: AutocompleteItem) -> bool:
        """
        Index an AutocompleteItem model instance.
        
        Args:
            item: AutocompleteItem instance
            
        Returns:
            True if indexed successfully
        """
        return self.index_item(item.to_es_document())
    
    def bulk_index(self, items: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Bulk index multiple autocomplete items.
        
        Args:
            items: List of dictionaries with autocomplete data
            
        Returns:
            Tuple of (success_count, failed_count)
        """
        if not items:
            logger.warning("No items to index")
            return (0, 0)
        
        try:
            actions = []
            now = datetime.utcnow().isoformat()
            
            for item in items:
                place_id = item.get('place_id')
                if not place_id:
                    logger.warning(f"Skipping item without place_id: {item.get('main_text', 'Unknown')}")
                    continue
                
                item['updated_at'] = now
                
                actions.append({
                    '_index': self.INDEX_NAME,
                    '_id': place_id,
                    '_source': item
                })
            
            success, failed = bulk(
                self.es,
                actions,
                stats_only=True,
                raise_on_error=False
            )
            
            logger.info(f"Bulk indexed: {success} success, {failed} failed")
            return (success, failed)
            
        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            return (0, len(items))
    
    # =========================================================================
    # SEARCH
    # =========================================================================
    
    def search(
        self,
        query: str,
        limit: int = 10,
        types: Optional[List[str]] = None,
        location: Optional[Dict[str, float]] = None,
        min_score: float = 40.0
    ) -> List[Dict[str, Any]]:
        """
        Autocomplete search with edge n-gram matching.
        
        Args:
            query: Search query string
            limit: Max results to return (1-20)
            types: Filter by place types (e.g., ['locality', 'neighborhood'])
            location: Dict with 'lat' and 'lng' for geo-distance boosting
            min_score: Minimum relevance score threshold
            
        Returns:
            List of autocomplete suggestions with scores
        """
        try:
            # Build should clauses for multi-field matching
            should_clauses = [
                # Exact prefix match on keyword (highest boost)
                {
                    "prefix": {
                        "main_text.keyword": {
                            "value": query,
                            "boost": 10.0  # Increased from 5.0
                        }
                    }
                },
                # Match phrase prefix for exact phrase matching
                {
                    "match_phrase_prefix": {
                        "main_text": {
                            "query": query,
                            "boost": 8.0,  # High boost for phrase prefix
                            "slop": 0,  # No word distance allowed
                            "max_expansions": 50
                        }
                    }
                },
                # Match phrase prefix on unaccented for Vietnamese
                {
                    "match_phrase_prefix": {
                        "main_text_unaccented": {
                            "query": query,
                            "boost": 7.0,
                            "slop": 0,
                            "max_expansions": 50
                        }
                    }
                },
                # Edge n-gram match on main_text (lower boost)
                {
                    "match": {
                        "main_text": {
                            "query": query,
                            "boost": 3.0
                        }
                    }
                },
                # Edge n-gram match on unaccented (for Vietnamese, etc.)
                {
                    "match": {
                        "main_text_unaccented": {
                            "query": query,
                            "boost": 2.5
                        }
                    }
                },
            ]
            
            # Build filter clauses
            filter_clauses = []
            if types:
                filter_clauses.append({"terms": {"types": types}})
            
            # Build function score query
            functions = [
                # Popularity boost based on click_count (very small factor for multiply mode)
                {
                    "field_value_factor": {
                        "field": "click_count",
                        "factor": 1.01,  # Very small multiplicative boost (1% per click)
                        "modifier": "log1p",
                        "missing": 1
                    }
                }
            ]
            
            # Add geo-distance decay function if location provided
            if location and location.get('lat') and location.get('lng'):
                functions.append({
                    "gauss": {
                        "location": {
                            "origin": {
                                "lat": location['lat'],
                                "lon": location['lng']
                            },
                            "scale": "50km",
                            "offset": "5km",
                            "decay": 0.5
                        }
                    },
                    "weight": 1.5
                })
            
            # Build the final query
            search_body = {
                "query": {
                    "function_score": {
                        "query": {
                            "bool": {
                                "should": should_clauses,
                                "minimum_should_match": 1,
                                "filter": filter_clauses if filter_clauses else []
                            }
                        },
                        # "functions": functions,
                        "score_mode": "multiply",
                        "boost_mode": "multiply"  # Multiplicative: requires BOTH good text match AND good metadata
                    }
                },
                "min_score": min_score,
                "size": limit,
                "_source": [
                    "place_id",
                    "description",
                    "main_text",
                    "secondary_text",
                    "terms",
                    "types",
                    "lat",
                    "lng",
                    "status",
                    "click_count"
                ]
            }
            
            # Execute search
            response = self.es.search(index=self.INDEX_NAME, body=search_body)
            
            # Extract results
            results = []
            for hit in response['hits']['hits']:
                item = hit['_source']
                item['_score'] = hit['_score']
                results.append(item)
            
            logger.debug(f"Autocomplete search '{query}' returned {len(results)} results")
            return results
            
        except NotFoundError:
            logger.warning(f"Index {self.INDEX_NAME} not found")
            return []
        except Exception as e:
            logger.error(f"Autocomplete search failed: {e}")
            return []
    
    def get_by_place_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Get autocomplete item by place_id.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            Item dict or None if not found
        """
        try:
            result = self.es.get(index=self.INDEX_NAME, id=place_id)
            return result['_source']
        except NotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get item by place_id: {e}")
            return None
    
    def exists(self, place_id: str) -> bool:
        """Check if item exists in index."""
        try:
            return self.es.exists(index=self.INDEX_NAME, id=place_id)
        except Exception:
            return False
    
    # =========================================================================
    # UPDATES
    # =========================================================================
    
    def update_status(self, place_id: str, status: CacheStatus) -> bool:
        """
        Update item status (pending -> cached).
        
        Args:
            place_id: Google Place ID
            status: New status
            
        Returns:
            True if updated successfully
        """
        try:
            self.es.update(
                index=self.INDEX_NAME,
                id=place_id,
                body={
                    "doc": {
                        "status": status.value,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                }
            )
            logger.debug(f"Updated status for {place_id} to {status.value}")
            return True
        except NotFoundError:
            logger.warning(f"Item not found: {place_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
            return False
    
    def increment_click(self, place_id: str) -> bool:
        """
        Increment click_count for popularity tracking.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            True if updated successfully
        """
        try:
            self.es.update(
                index=self.INDEX_NAME,
                id=place_id,
                body={
                    "script": {
                        "source": "ctx._source.click_count += 1; ctx._source.updated_at = params.now",
                        "params": {
                            "now": datetime.utcnow().isoformat()
                        }
                    }
                }
            )
            logger.debug(f"Incremented click_count for {place_id}")
            return True
        except NotFoundError:
            logger.warning(f"Item not found: {place_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to increment click: {e}")
            return False
    
    def update_location(self, place_id: str, lat: float, lng: float) -> bool:
        """
        Update item location (after resolving Place Details).
        
        Args:
            place_id: Google Place ID
            lat: Latitude
            lng: Longitude
            
        Returns:
            True if updated successfully
        """
        try:
            self.es.update(
                index=self.INDEX_NAME,
                id=place_id,
                body={
                    "doc": {
                        "lat": lat,
                        "lng": lng,
                        "location": {"lat": lat, "lon": lng},
                        "status": CacheStatus.CACHED.value,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                }
            )
            logger.debug(f"Updated location for {place_id}")
            return True
        except NotFoundError:
            logger.warning(f"Item not found: {place_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to update location: {e}")
            return False
    
    # =========================================================================
    # DELETE
    # =========================================================================
    
    def delete_by_place_id(self, place_id: str) -> bool:
        """
        Delete item by place_id.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            True if deleted successfully
        """
        try:
            self.es.delete(index=self.INDEX_NAME, id=place_id)
            logger.debug(f"Deleted autocomplete item: {place_id}")
            return True
        except NotFoundError:
            logger.warning(f"Item not found: {place_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete item: {e}")
            return False
    
    def delete_stale_items(self, days: int = 90) -> int:
        """
        Delete items not clicked in X days.
        
        Args:
            days: Delete items older than this many days
            
        Returns:
            Number of deleted items
        """
        try:
            result = self.es.delete_by_query(
                index=self.INDEX_NAME,
                body={
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"status": "pending"}},
                                {"range": {"updated_at": {"lt": f"now-{days}d"}}}
                            ]
                        }
                    }
                }
            )
            deleted = result.get('deleted', 0)
            logger.info(f"Deleted {deleted} stale autocomplete items (older than {days} days)")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete stale items: {e}")
            return 0
