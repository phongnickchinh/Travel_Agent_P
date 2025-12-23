"""
Elasticsearch Repository Interfaces Package

Note: ESAdminLocationRepositoryInterface, ESRegionRepositoryInterface removed (2025-01 migration)
"""

from .es_poi_repository_interface import ESPOIRepositoryInterface
from .es_autocomplete_repository_interface import ESAutocompleteRepositoryInterface

__all__ = [
    'ESPOIRepositoryInterface',
    'ESAutocompleteRepositoryInterface'
]
