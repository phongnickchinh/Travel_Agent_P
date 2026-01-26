import logging
import time
from typing import List, Dict, Optional, Any
from pathlib import Path
import json

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from .base_es_repository import BaseESRepository
from .interfaces import ESPOIRepositoryInterface
from config import Config

logger = logging.getLogger(__name__)


class ESPOIRepository(BaseESRepository, ESPOIRepositoryInterface):
    INDEX_NAME = Config.ELASTICSEARCH_POI_INDEX
    MAPPING_FILE = None

    def __init__(self, es_client: Optional[Elasticsearch] = None):
        self.INDEX_NAME = Config.ELASTICSEARCH_POI_INDEX
        super().__init__(es_client)

    def _load_mapping(self) -> Dict:
        try:
            config_path = Config.ELASTICSEARCH_CONFIG_FILE_PATH
            if not Path(config_path).is_absolute():
                project_root = Path(__file__).parent.parent.parent.parent
                mapping_file = project_root / config_path
            else:
                mapping_file = Path(config_path)
            if not mapping_file.exists():
                raise FileNotFoundError(f"ES mapping file not found: {mapping_file}")
            with open(mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load ES mapping: {e}")
            raise

    def index_poi(self, poi_data: Dict, poi_id: Optional[str] = None) -> bool:
        try:
            doc_id = poi_id or poi_data.get('poi_id') or poi_data.get('_id')
            if not doc_id:
                return False
            es_doc = self._transform_to_es_document(poi_data)
            self.es.index(index=self.INDEX_NAME, id=doc_id, document=es_doc)
            return True
        except Exception as e:
            logger.error(f"Failed to index POI: {e}")
            return False

    def bulk_index(self, pois: List[Dict]) -> tuple[int, int]:
        if not pois:
            return (0, 0)
        try:
            actions = []
            for poi in pois:
                doc_id = poi.get('poi_id') or poi.get('_id')
                if not doc_id:
                    continue
                es_doc = self._transform_to_es_document(poi)
                actions.append({'_index': self.INDEX_NAME, '_id': doc_id, '_source': es_doc})
            success, failed = bulk(self.es, actions, stats_only=True, raise_on_error=False)
            logger.info(f"Bulk indexed: {success} success, {failed} failed")
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
            
            return results
        except Exception as e:
            logger.error(f"Autocomplete failed: {e}")
            return []

    def delete_poi(self, poi_id: str) -> bool:
        return self.delete_by_id(poi_id)

    def _transform_to_es_document(self, poi_data: Dict) -> Dict:
        # === LOCATION: Handle both GeoJSON and flat formats ===
        location = poi_data.get('location', {})
        lat = 0.0
        lon = 0.0
        
        if isinstance(location, dict):
            # GeoJSON format from GooglePlacesProvider: {type: "Point", coordinates: [lng, lat]}
            if 'coordinates' in location:
                coords = location.get('coordinates', [0, 0])
                if len(coords) >= 2:
                    lon = coords[0]  # GeoJSON: [lng, lat]
                    lat = coords[1]
            # Flat format: {latitude: ..., longitude: ...}
            elif 'latitude' in location:
                lat = location.get('latitude', 0.0)
                lon = location.get('longitude', 0.0)
            # ES format: {lat: ..., lon: ...}
            elif 'lat' in location:
                lat = location.get('lat', 0.0)
                lon = location.get('lon', 0.0)
        
        # === ADDRESS: Handle nested and flat formats ===
        address = poi_data.get('address', {})
        address_str = ''
        if isinstance(address, dict):
            # Provider format: {full_address: ..., short_address: ...}
            address_str = address.get('full_address', address.get('formatted', ''))
        elif isinstance(address, str):
            address_str = address
        
        # === RATING: Handle nested 'ratings' and flat 'rating' formats ===
        ratings = poi_data.get('ratings', {})
        rating_value = 0.0
        total_reviews = 0
        
        if isinstance(ratings, dict):
            # Provider format: {average: ..., count: ...}
            rating_value = ratings.get('average', 0.0)
            total_reviews = ratings.get('count', 0)
        else:
            # Flat format or legacy
            rating_data = poi_data.get('rating', {})
            if isinstance(rating_data, dict):
                rating_value = rating_data.get('value', 0.0)
                total_reviews = rating_data.get('total_reviews', 0)
            else:
                rating_value = float(rating_data) if rating_data else 0.0
                total_reviews = poi_data.get('total_reviews', poi_data.get('user_ratings_total', 0))
        
        # === CONTACT: Handle nested format ===
        contact = poi_data.get('contact', {})
        phone = contact.get('phone', '') if isinstance(contact, dict) else ''
        website = contact.get('website', '') if isinstance(contact, dict) else ''
        google_maps_uri = contact.get('google_maps_uri', '') if isinstance(contact, dict) else poi_data.get('google_maps_uri', '')
        
        # === DESCRIPTION: Handle nested format ===
        description = poi_data.get('description', {})
        description_str = ''
        if isinstance(description, dict):
            description_str = description.get('long', description.get('short', ''))
        elif isinstance(description, str):
            description_str = description
        
        # === PRICING: Handle nested format ===
        pricing = poi_data.get('pricing', {})
        price_level = ''
        if isinstance(pricing, dict):
            price_level = pricing.get('level', '')
        else:
            price_level = poi_data.get('price_level', '')
        
        # === PHOTOS: Handle 'images' (provider) or 'photos' (legacy) ===
        photos = poi_data.get('images', poi_data.get('photos', []))
        photo_refs = []
        if isinstance(photos, list):
            for p in photos[:5]:
                if isinstance(p, dict):
                    ref = p.get('photo_reference', p.get('url', p.get('reference', '')))
                    if ref:
                        photo_refs.append(ref)
                elif isinstance(p, str):
                    photo_refs.append(p)
        
        # === REVIEWS ===
        reviews = poi_data.get('reviews', [])
        google_data = poi_data.get('google_data', {})
        if not reviews and google_data:
            reviews = google_data.get('reviews', [])
        
        # === PROVIDER: Handle nested format ===
        provider = poi_data.get('provider', {})
        provider_name = ''
        provider_id = ''
        if isinstance(provider, dict):
            provider_name = provider.get('name', 'google_places')
            provider_id = provider.get('place_id', '')
        else:
            provider_name = str(provider) if provider else 'google_places'
            provider_id = poi_data.get('provider_id', '')
        
        # === TYPES: Use categories if types not available ===
        types = poi_data.get('types', poi_data.get('categories', []))
        primary_type = poi_data.get('primary_type', '')
        if not primary_type and google_data:
            primary_type = google_data.get('primary_type', '')
        if not primary_type and types:
            primary_type = types[0] if isinstance(types, list) and types else ''
        
        # === METADATA: Get timestamps ===
        metadata = poi_data.get('metadata', {})
        created_at = metadata.get('created_at') if isinstance(metadata, dict) else poi_data.get('created_at')
        updated_at = metadata.get('updated_at') if isinstance(metadata, dict) else poi_data.get('updated_at')
        
        # === BUSINESS STATUS ===
        business_status = poi_data.get('business_status', '')
        if not business_status and google_data:
            business_status = google_data.get('business_status', '')
        
        es_doc = {
            'poi_id': poi_data.get('poi_id') or poi_data.get('_id'),
            'dedupe_key': poi_data.get('dedupe_key'),
            'provider': provider_name,
            'provider_id': provider_id,
            
            'name': poi_data.get('name', ''),
            'types': types,
            'primary_type': primary_type,
            
            # ES geo_point format: {"lat": ..., "lon": ...}
            'location': {
                'lat': lat,
                'lon': lon
            },
            
            'address': address_str,
            
            'rating': rating_value,
            'total_reviews': total_reviews,
            
            'price_level': price_level,
            
            'phone': phone,
            'website': website,
            
            'description': description_str,
            
            'business_status': business_status,
            'google_maps_uri': google_maps_uri,
            
            'photos_count': len(photos) if isinstance(photos, list) else 0,
            'photos': photo_refs,
            
            'reviews_count': len(reviews) if isinstance(reviews, list) else 0,
            
            'amenities': poi_data.get('amenities', {}),
            'opening_hours': poi_data.get('opening_hours', {}),
            
            'created_at': created_at,
            'updated_at': updated_at,
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