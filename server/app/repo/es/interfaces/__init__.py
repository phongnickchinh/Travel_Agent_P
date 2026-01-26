"""
Elasticsearch Repository Interfaces Package

Note: ESAdminLocationRepositoryInterface, ESRegionRepositoryInterface removed (2025-01 migration)
"""

from .es_poi_repository_interface import ESPOIRepositoryInterface
from .es_autocomplete_repository_interface import ESAutocompleteRepositoryInterface
from .es_plan_repository_interface import ESPlanRepositoryInterface

__all__ = [
    'ESPOIRepositoryInterface',
    'ESAutocompleteRepositoryInterface',
    'ESPlanRepositoryInterface'
]
