import logging
from typing import List, Dict, Optional, Tuple

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from .base_es_repository import BaseESRepository
from .interfaces import ESPlanRepositoryInterface
from ...model.mongo.plan import Plan

logger = logging.getLogger(__name__)


class ESPlanRepository(BaseESRepository, ESPlanRepositoryInterface):
    INDEX_NAME = "plans"
    MAPPING_FILE = "plan_mapping.json"

    def index_plan(self, plan: dict) -> bool:
        doc = {
            "plan_id": plan['plan_id'],
            "user_id": plan['user_id'],
            "destination": plan['destination'],
            "title": plan['title']
        }
        return self.index_document(doc, doc_id=plan['plan_id'])

    def bulk_index(self, plans: List[Dict]) -> Tuple[int, int]:
        if not plans:
            return (0, 0)
        try:
            actions = []
            for p in plans:
                doc = {
                    "plan_id": p.get("plan_id"),
                    "user_id": p.get("user_id"),
                    "destination": p.get("destination"),
                    "title": p.get("title")
                }
                actions.append({
                    "_index": self.INDEX_NAME,
                    "_id": doc["plan_id"],
                    "_source": doc
                })
            success, failed = bulk(self.es, actions, stats_only=True, raise_on_error=False)
            logger.info(f"Bulk indexed plans: {success} success, {failed} failed")
            return (success, failed)
        except Exception as e:
            logger.error(f"Bulk indexing plans failed: {e}")
            return (0, len(plans))

    def index_plans_bulk(self, plans: List[Plan]) -> bool:
        dicts = [{"plan_id": p.plan_id, "user_id": p.user_id, "destination": p.destination, "title": p.title} for p in plans]
        success, _ = self.bulk_index(dicts)
        return success == len(plans)

    def search(self, query: str, user_id: Optional[str] = None, limit: int = 20, offset: int = 0) -> Dict:
        try:
            should_clauses = []
            if query:
                should_clauses = [
                    {"prefix": {"title.keyword": {"value": query, "boost": 10.0}}},
                    {"match_phrase_prefix": {"title": {"query": query, "boost": 8.0, "slop": 0, "max_expansions": 50}}},
                    {"match_phrase_prefix": {"destination": {"query": query, "boost": 6.0, "slop": 0, "max_expansions": 50}}},
                    {"multi_match": {
                        "query": query,
                        "fields": ["title^3", "title.edge_ngram^2", "destination", "destination.edge_ngram"],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }}
                ]
            
            filter_clauses = []
            if user_id:
                filter_clauses.append({"term": {"user_id": user_id}})
            
            bool_query = {
                "bool": {
                    "should": should_clauses if should_clauses else [{"match_all": {}}],
                    "minimum_should_match": 1 if should_clauses else 0,
                    "filter": filter_clauses
                }
            }
            
            response = self.es.search(
                index=self.INDEX_NAME,
                query=bool_query,
                size=limit,
                from_=offset,
                track_total_hits=True
            )
            hits = response["hits"]["hits"]
            total = response["hits"]["total"]["value"] if isinstance(response["hits"]["total"], dict) else response["hits"]["total"]
            results = [{"plan_id": h["_source"]["plan_id"], "title": h["_source"].get("title"), "destination": h["_source"].get("destination"), "_score": h["_score"]} for h in hits]
            return {"results": results, "total": total, "took_ms": response.get("took", 0)}
        except Exception as e:
            logger.error(f"Search plans failed: {e}")
            return {"results": [], "total": 0, "took_ms": 0}

    def search_plans(self, query: str, limit: int = 10, offset: int = 0) -> Tuple[List[Plan], int]:
        result = self.search(query, limit=limit, offset=offset)
        return (result["results"], result["total"])

    def delete_plan(self, plan_id: str) -> bool:
        return self.delete_by_id(plan_id)
