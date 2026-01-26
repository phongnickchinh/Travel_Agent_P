import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

from elasticsearch.helpers import bulk
from elasticsearch.exceptions import NotFoundError

from ...model.mongo.autocomplete_cache import AutocompleteItem, CacheStatus
from .interfaces import ESAutocompleteRepositoryInterface
from .base_es_repository import BaseESRepository

logger = logging.getLogger(__name__)


class ESAutocompleteRepository(BaseESRepository, ESAutocompleteRepositoryInterface):
    
    INDEX_NAME = "autocomplete"
    MAPPING_FILE = "autocomplete_cache_mapping.json"
    
    def count_by_status(self, status: str) -> int:
        try:
            result = self.es.count(index=self.INDEX_NAME)
            return result.get('count', 0)
        except Exception as e:
            logger.error(f"Failed to count documents: {e}")
            return 0
    
    def index_item(self, item: Dict[str, Any]) -> bool:
        place_id = item.get('place_id')
        if not place_id:
            return False
        item['updated_at'] = datetime.utcnow().isoformat()
        return self.index_document(place_id, item)
    
    def index_from_model(self, item: AutocompleteItem) -> bool:
        return self.index_item(item.to_es_document())
    
    def bulk_index(self, items: List[Dict[str, Any]]) -> Tuple[int, int]:
        if not items:
            return (0, 0)
        try:
            actions = []
            now = datetime.utcnow().isoformat()
            for item in items:
                place_id = item.get('place_id')
                if not place_id:
                    continue
                item['updated_at'] = now
                actions.append({
                    '_index': self.INDEX_NAME,
                    '_id': place_id,
                    '_source': item
                })
            success, failed = bulk(self.es, actions, stats_only=True, raise_on_error=False)
            logger.info(f"Bulk indexed: {success} success, {failed} failed")
            return (success, failed)
        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            return (0, len(items))
    
    def search(
        self,
        query: str,
        limit: int = 10,
        types: Optional[List[str]] = None,
        location: Optional[Dict[str, float]] = None,
        min_score: float = 40.0
    ) -> List[Dict[str, Any]]:
        try:
            should_clauses = [
                {"prefix": {"main_text.keyword": {"value": query, "boost": 10.0}}},
                {"match_phrase_prefix": {"main_text": {"query": query, "boost": 8.0, "slop": 0, "max_expansions": 50}}},
                {"match_phrase_prefix": {"main_text_unaccented": {"query": query, "boost": 7.0, "slop": 0, "max_expansions": 50}}},
                {"match": {"main_text": {"query": query, "boost": 3.0}}},
                {"match": {"main_text_unaccented": {"query": query, "boost": 2.5}}},
            ]
            
            filter_clauses = []
            if types:
                filter_clauses.append({"terms": {"types": types}})
            
            functions = [
                {"field_value_factor": {"field": "click_count", "factor": 1.01, "modifier": "log1p", "missing": 1}}
            ]
            
            if location and location.get('lat') and location.get('lng'):
                functions.append({
                    "gauss": {
                        "location": {"origin": {"lat": location['lat'], "lon": location['lng']}, "scale": "50km", "offset": "5km", "decay": 0.5}
                    },
                    "weight": 1.5
                })
            
            search_body = {
                "query": {
                    "function_score": {
                        "query": {"bool": {"should": should_clauses, "minimum_should_match": 1, "filter": filter_clauses if filter_clauses else []}},
                        "score_mode": "multiply",
                        "boost_mode": "multiply"
                    }
                },
                "min_score": min_score,
                "size": limit,
                "_source": ["place_id", "description", "main_text", "secondary_text", "terms", "types", "lat", "lng", "status", "click_count"]
            }
            
            response = self.es.search(index=self.INDEX_NAME, body=search_body)
            results = []
            for hit in response['hits']['hits']:
                item = hit['_source']
                item['_score'] = hit['_score']
                results.append(item)
            return results
        except NotFoundError:
            return []
        except Exception as e:
            logger.error(f"Autocomplete search failed: {e}")
            return []
    
    def get_by_place_id(self, place_id: str) -> Optional[Dict[str, Any]]:
        return self.get_by_id(place_id)
    
    def exists(self, place_id: str) -> bool:
        try:
            return self.es.exists(index=self.INDEX_NAME, id=place_id)
        except Exception:
            return False
    # =========================================================================
    
    def update_status(self, place_id: str, status: CacheStatus) -> bool:
        try:
            self.es.update(
                index=self.INDEX_NAME,
                id=place_id,
                body={"doc": {"status": status.value, "updated_at": datetime.utcnow().isoformat()}}
            )
            return True
        except NotFoundError:
            return False
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
            return False
    
    def increment_click(self, place_id: str) -> bool:
        try:
            self.es.update(
                index=self.INDEX_NAME,
                id=place_id,
                body={
                    "script": {
                        "source": "ctx._source.click_count += 1; ctx._source.updated_at = params.now",
                        "params": {"now": datetime.utcnow().isoformat()}
                    }
                }
            )
            return True
        except NotFoundError:
            return False
        except Exception as e:
            logger.error(f"Failed to increment click: {e}")
            return False
    
    def update_location(self, place_id: str, lat: float, lng: float) -> bool:
        try:
            self.es.update(
                index=self.INDEX_NAME,
                id=place_id,
                body={
                    "doc": {
                        "lat": lat, "lng": lng,
                        "location": {"lat": lat, "lon": lng},
                        "status": CacheStatus.CACHED.value,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                }
            )
            return True
        except NotFoundError:
            return False
        except Exception as e:
            logger.error(f"Failed to update location: {e}")
            return False
    
    def delete_by_place_id(self, place_id: str) -> bool:
        return self.delete_by_id(place_id)
    
    def delete_stale_items(self, days: int = 90) -> int:
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
            return result.get('deleted', 0)
        except Exception as e:
            logger.error(f"Failed to delete stale items: {e}")
            return 0
