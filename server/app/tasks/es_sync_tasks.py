"""
Elasticsearch Sync Tasks
========================

Background tasks for syncing data from MongoDB to Elasticsearch.
These tasks run asynchronously to avoid blocking app startup.

Author: Travel Agent P Team
"""

import logging
from app import celery
from app.core.es_initializer import get_es_initializer

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_elasticsearch_data(self):
    try:
        logger.info("[ES_SYNC_TASK] Starting Elasticsearch sync...")
        
        es_initializer = get_es_initializer()
        
        if not es_initializer.is_connected():
            logger.warning("[ES_SYNC_TASK] Elasticsearch not connected, skipping sync")
            return {"status": "skipped", "reason": "ES not connected"}
        
        # Sync POIs
        poi_indexed, poi_failed = es_initializer.sync_pois()
        logger.info(f"[ES_SYNC_TASK] POI sync: {poi_indexed} indexed, {poi_failed} failed")
        
        # Sync Autocomplete
        auto_indexed, auto_failed = es_initializer.sync_autocomplete()
        logger.info(f"[ES_SYNC_TASK] Autocomplete sync: {auto_indexed} indexed, {auto_failed} failed")
        
        # Sync Plans
        plan_indexed, plan_failed = es_initializer.sync_plans()
        logger.info(f"[ES_SYNC_TASK] Plan sync: {plan_indexed} indexed, {plan_failed} failed")
        
        logger.info("[ES_SYNC_TASK] Elasticsearch sync completed successfully")
        
        return {
            "status": "success",
            "poi": {"indexed": poi_indexed, "failed": poi_failed},
            "autocomplete": {"indexed": auto_indexed, "failed": auto_failed},
            "plans": {"indexed": plan_indexed, "failed": plan_failed}
        }
        
    except Exception as e:
        logger.error(f"[ES_SYNC_TASK] Elasticsearch sync failed: {e}")
        
        # Retry the task
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error("[ES_SYNC_TASK] Max retries exceeded for ES sync")
            return {"status": "failed", "error": str(e)}