"""
Elasticsearch POI Repository
Manages POI indexing and search operations in Elasticsearch
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch.exceptions import NotFoundError, RequestError

from ...core.clients.elasticsearch_client import ElasticsearchClient
from ...repo.es.interfaces import ESPOIRepositoryInterface
from config import Config

logger = logging.getLogger(__name__)


class ESPOIRepository(ESPOIRepositoryInterface):
    """
    Elasticsearch repository for POI search and indexing
    
    Features:
    - Index management (create, delete, update mappings)
    - Bulk indexing from MongoDB
    - Autocomplete search with edge n-gram
    - Geo-distance search
    - Full-text search with filters
    - Aggregations for analytics
    
    Usage:
        repo = ESPOIRepository()
        
        # Create index
        repo.create_index()
        
        # Index a POI
        repo.index_poi(poi_data)
        
        # Search
        results = repo.search(query="cafe", location={...}, radius=5000)
    """
    
    def __init__(self, es_client: Optional[Elasticsearch] = None):
        """
        Initialize ES POI Repository
        
        Args:
            es_client: Elasticsearch client (defaults to singleton)
        """
        self.es = es_client or ElasticsearchClient.get_instance()
        
        # Load index name from config
        self.INDEX_NAME = Config.ELASTICSEARCH_POI_INDEX
        
        # Load index mapping from JSON file
        self.INDEX_MAPPING = self._load_index_mapping()
        
        logger.info(f"Initialized ESPOIRepository with index: {self.INDEX_NAME}")
    
    def _load_index_mapping(self) -> Dict:
        """
        Load index mapping configuration from JSON file
        
        Returns:
            Dict: Index mapping configuration
        """
        try:
            # Get mapping file path from config (relative to project root)
            config_path = Config.ELASTICSEARCH_CONFIG_FILE_PATH
            
            # Resolve absolute path (assume config path is relative to server root)
            if not Path(config_path).is_absolute():
                project_root = Path(__file__).parent.parent.parent.parent  # Go up to server/
                mapping_file = project_root / config_path
            else:
                mapping_file = Path(config_path)
            
            if not mapping_file.exists():
                logger.error(f"Mapping file not found: {mapping_file}")
                raise FileNotFoundError(f"ES mapping file not found: {mapping_file}")
            
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            
            logger.info(f"Loaded ES mapping from: {mapping_file}")
            return mapping
            
        except Exception as e:
            logger.error(f"Failed to load ES mapping: {e}")
            raise
        logger.info(f"Initialized ESPOIRepository with index: {self.INDEX_NAME}")
    
    def create_index(self, delete_if_exists: bool = False) -> bool:
        """
        Create POI index with mapping
        
        Args:
            delete_if_exists: Delete existing index before creating
            
        Returns:
            True if created successfully
        """
        try:
            # Check if index exists
            if self.es.indices.exists(index=self.INDEX_NAME):
                if delete_if_exists:
                    logger.warning(f"Deleting existing index: {self.INDEX_NAME}")
                    self.es.indices.delete(index=self.INDEX_NAME)
                else:
                    logger.info(f"Index {self.INDEX_NAME} already exists")
                    return True
            
            # Create index
            self.es.indices.create(index=self.INDEX_NAME, body=self.INDEX_MAPPING)
            logger.info(f"[INFO] Created index: {self.INDEX_NAME}")
            return True
            
        except RequestError as e:
            logger.error(f"Failed to create index: {e}")
            return False
    
    def delete_index(self) -> bool:
        """
        Delete POI index
        
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
            logger.error(f"Failed to delete index: {e}")
            return False
    
    def index_poi(self, poi_data: Dict, poi_id: Optional[str] = None) -> bool:
        """
        Index a single POI document
        
        Args:
            poi_data: POI dictionary (from MongoDB or provider)
            poi_id: Optional document ID (defaults to poi_data['poi_id'])
            
        Returns:
            True if indexed successfully
        """
        try:
            doc_id = poi_id or poi_data.get('poi_id') or poi_data.get('_id')
            
            if not doc_id:
                logger.error("Cannot index POI without ID")
                return False
            es_doc = self._transform_to_es_document(poi_data)
            
            # Index document
            self.es.index(index=self.INDEX_NAME, id=doc_id, document=es_doc)
            
            logger.debug(f"Indexed POI: {es_doc.get('name', 'Unknown')} (ID: {doc_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index POI: {e}")
            return False
    
    def bulk_index(self, pois: List[Dict]) -> tuple[int, int]:
        """
        Bulk index multiple POIs
        
        Args:
            pois: List of POI dictionaries
            
        Returns:
            Tuple of (success_count, failed_count)
        """
        if not pois:
            logger.warning("No POIs to index")
            return (0, 0)
        
        try:
            # Prepare bulk actions
            actions = []
            for poi in pois:
                doc_id = poi.get('poi_id') or poi.get('_id')
                
                if not doc_id:
                    logger.warning(f"Skipping POI without ID: {poi.get('name', 'Unknown')}")
                    continue
                
                es_doc = self._transform_to_es_document(poi)
                
                actions.append({
                    '_index': self.INDEX_NAME,
                    '_id': doc_id,
                    '_source': es_doc
                })
            
            # Execute bulk indexing
            success, failed = bulk(
                self.es,
                actions,
                stats_only=True,
                raise_on_error=False
            )
            
            logger.info(f"Bulk indexed: {success} success, {failed} failed (total: {len(pois)})")
            
            return (success, failed)
            
        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            return (0, len(pois))
    
    def search(
        self,
        query: str,
        location: Optional[Dict[str, float]] = None,
        radius_km: float = 5.0,
        types: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        price_levels: Optional[List[str]] = None,
        sort_by: str = "relevance",
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search POIs with filters
        
        Args:
            query: Search query string
            location: Dict with 'latitude' and 'longitude' for geo search
            radius_km: Search radius in kilometers
            types: Filter by POI types
            min_rating: Minimum rating filter
            price_levels: List of price levels to filter
            sort_by: Sort order - "relevance", "distance", "rating"
            limit: Number of results to return
            offset: Pagination offset
            
        Returns:
            Dict with results, total, took_ms
        """
        import time
        start_time = time.time()
        
        try:
            must_clauses = []
            filter_clauses = []
            
            # Text search on name and description
            if query:
                must_clauses.append({
                    "multi_match": {
                        "query": query,
                        "fields": ["name^3", "name.edge_ngram^2", "description"],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                })
            
            # Geo-distance filter
            if location:
                filter_clauses.append({
                    "geo_distance": {
                        "distance": f"{radius_km}km",
                        "location": {
                            "lat": location.get('latitude'),
                            "lon": location.get('longitude')
                        }
                    }
                })
            
            # Type filter
            if types:
                filter_clauses.append({"terms": {"types": types}})
            
            # Rating filter
            if min_rating is not None:
                filter_clauses.append({"range": {"rating": {"gte": min_rating}}})
            
            # Price level filter (accept list)
            if price_levels:
                filter_clauses.append({"terms": {"price_level": price_levels}})
            
            search_query = {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses
                }
            }
            
            # Build sort based on sort_by parameter
            sort = []
            if sort_by == "distance" and location:
                sort.append({
                    "_geo_distance": {
                        "location": {
                            "lat": location.get('latitude'),
                            "lon": location.get('longitude')
                        },
                        "order": "asc",
                        "unit": "km"
                    }
                })
            elif sort_by == "rating":
                sort.append({"rating": {"order": "desc"}})
            elif sort_by == "popularity":
                sort.append({"total_reviews": {"order": "desc"}})
            else:
                # Default relevance - add distance as secondary sort if location provided
                if location:
                    sort.append({
                        "_geo_distance": {
                            "location": {
                                "lat": location.get('latitude'),
                                "lon": location.get('longitude')
                            },
                            "order": "asc",
                            "unit": "km"
                        }
                    })
                sort.append("_score")
            
            # Execute search with track_total_hits for accurate count
            response = self.es.search(
                index=self.INDEX_NAME,
                query=search_query,
                sort=sort,
                size=limit,
                from_=offset,
                track_total_hits=True
            )
            
            took_ms = int((time.time() - start_time) * 1000)
            hits = response['hits']['hits']
            total = response['hits']['total']['value'] if isinstance(response['hits']['total'], dict) else response['hits']['total']
            
            results = []
            for hit in hits:
                result = self._transform_from_es_document(hit['_source'], location)
                result['_score'] = hit['_score']
                result['_id'] = hit['_id']
                
                # Add distance if geo search
                if 'sort' in hit and len(hit['sort']) > 0 and isinstance(hit['sort'][0], (int, float)):
                    result['_distance_km'] = round(hit['sort'][0], 2)
                
                results.append(result)
            
            logger.info(f"Search '{query}' returned {len(results)}/{total} results in {took_ms}ms")
            
            return {
                "results": results,
                "total": total,
                "took_ms": took_ms
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "results": [],
                "total": 0,
                "took_ms": int((time.time() - start_time) * 1000)
            }
    
    def autocomplete(self, prefix: str, size: int = 10) -> List[Dict]:
        """
        Autocomplete search using edge n-gram
        
        Args:
            prefix: Search prefix (e.g., "res" for "restaurant")
            size: Max results to return
            
        Returns:
            List of POI suggestions
        """
        try:
            search_query = {
                "match": {
                    "name.edge_ngram": {
                        "query": prefix,
                        "operator": "and"
                    }
                }
            }
            
            response = self.es.search(
                index=self.INDEX_NAME,
                query=search_query,
                size=size,
                _source=["poi_id", "name", "types", "rating", "address"]
            )
            
            results = [hit['_source'] for hit in response['hits']['hits']]
            
            logger.debug(f"Autocomplete '{prefix}' returned {len(results)} suggestions")
            
            return results
            
        except Exception as e:
            logger.error(f"Autocomplete failed: {e}")
            return []
    
    def get_by_id(self, poi_id: str) -> Optional[Dict]:
        """
        Get POI by ID
        
        Args:
            poi_id: POI identifier
            
        Returns:
            POI dictionary or None if not found
        """
        try:
            response = self.es.get(index=self.INDEX_NAME, id=poi_id)
            return response['_source']
        except NotFoundError:
            logger.debug(f"POI not found: {poi_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get POI: {e}")
            return None
    
    def delete_poi(self, poi_id: str) -> bool:
        """
        Delete POI by ID
        
        Args:
            poi_id: POI identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            self.es.delete(index=self.INDEX_NAME, id=poi_id)
            logger.info(f"Deleted POI: {poi_id}")
            return True
        except NotFoundError:
            logger.warning(f"POI not found for deletion: {poi_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete POI: {e}")
            return False
    
    def _transform_to_es_document(self, poi_data: Dict) -> Dict:
        """
        Transform POI data to ES document format
        
        Flattens nested structures for better indexing
        
        Args:
            poi_data: Raw POI dictionary
            
        Returns:
            ES-optimized document dictionary
        """
        location = poi_data.get('location', {})
        address = poi_data.get('address', {})
        rating_data = poi_data.get('rating', {})
        contact = poi_data.get('contact', {})
        description = poi_data.get('description', {})
        photos = poi_data.get('photos', [])
        reviews = poi_data.get('reviews', [])
        es_doc = {
            'poi_id': poi_data.get('poi_id') or poi_data.get('_id'),
            'dedupe_key': poi_data.get('dedupe_key'),
            'provider': poi_data.get('provider'),
            'provider_id': poi_data.get('provider_id'),
            
            'name': poi_data.get('name', ''),
            'types': poi_data.get('types', []),
            'primary_type': poi_data.get('primary_type', ''),
            
            # Geo point (ES format: {"lat": ..., "lon": ...})
            'location': {
                'lat': location.get('latitude', 0.0),
                'lon': location.get('longitude', 0.0)
            },
            
            'address': address.get('formatted', ''),
            
            'rating': rating_data.get('value', 0.0),
            'total_reviews': rating_data.get('total_reviews', 0),
            
            'price_level': poi_data.get('price_level', ''),
            
            'phone': contact.get('phone', ''),
            'website': contact.get('website', ''),
            
            'description': description.get('long', description.get('short', '')),
            
            'business_status': poi_data.get('business_status', ''),
            'google_maps_uri': poi_data.get('google_maps_uri', ''),
            
            'photos_count': len(photos),
            'photos': [p.get('reference', '') for p in photos[:5]],
            
            'reviews_count': len(reviews),
            
            'amenities': poi_data.get('amenities', {}),
            'opening_hours': poi_data.get('opening_hours', {}),
            
            'created_at': poi_data.get('created_at'),
            'updated_at': poi_data.get('updated_at'),
            'fetched_at': poi_data.get('fetched_at')
        }
        
        return es_doc

    def _transform_from_es_document(self, es_doc: Dict, center_location: Optional[Dict] = None) -> Dict:
        """
        Transform ES document back to frontend-friendly format
        
        Converts ES geo_point back to latitude/longitude for frontend consumption
        
        Args:
            es_doc: ES document dictionary
            center_location: Optional center location for reference
            
        Returns:
            Frontend-friendly POI dictionary
        """
        location = es_doc.get('location', {})
        lat = location.get('lat', 0.0) if isinstance(location, dict) else 0.0
        lon = location.get('lon', 0.0) if isinstance(location, dict) else 0.0
        
        photos = es_doc.get('photos', [])
        primary_photo = photos[0] if photos else None
        
        return {
            'poi_id': es_doc.get('poi_id'),
            'name': es_doc.get('name', ''),
            'types': es_doc.get('types', []),
            'primary_type': es_doc.get('primary_type', ''),
            'category': es_doc.get('primary_type') or (es_doc.get('types', [''])[0] if es_doc.get('types') else ''),
            
            'location': {
                'latitude': lat,
                'longitude': lon
            },
            'latitude': lat,
            'longitude': lon,
            
            'address': es_doc.get('address', ''),
            
            'rating': es_doc.get('rating', 0.0),
            'total_reviews': es_doc.get('total_reviews', 0),
            
            'price_level': es_doc.get('price_level', ''),
            
            'description': es_doc.get('description', ''),
            
            'business_status': es_doc.get('business_status', ''),
            'google_maps_uri': es_doc.get('google_maps_uri', ''),
            
            'photo_reference': primary_photo,
            'photos': photos,
            'photos_count': es_doc.get('photos_count', 0),
            
            'opening_hours': es_doc.get('opening_hours', {}),
            
            'provider': es_doc.get('provider', ''),
            'provider_id': es_doc.get('provider_id', '')
        }

    def is_healthy(self) -> bool:
        """
        Check if Elasticsearch connection is healthy.
        
        Returns:
            True if ES is available and responsive, False otherwise
        """
        try:
            return self.es.ping()
        except Exception as e:
            logger.error(f"[ERROR] Elasticsearch health check failed: {e}")
            return False