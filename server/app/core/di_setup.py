"""
Dependency Injection Setup
===========================

Registers all dependencies (repositories, services) in the DI container.
"""

from .di_container import DIContainer

_is_initialized = False

def setup_dependencies():
    """Register all dependencies in the container."""
    global _is_initialized
    
    if _is_initialized:
        return
    
    # Import PostgreSQL interfaces
    from ..repo.postgre.interfaces.user_repository_interface import UserInterface
    from ..repo.postgre.interfaces.token_repository_interface import TokenInterface
    from ..repo.postgre.interfaces.role_repository_interface import RoleInterface, UserRoleInterface
    from ..repo.postgre.interfaces.cost_usage_interface import CostUsageInterface

    # Import MongoDB interfaces
    from ..repo.mongo.interfaces import POIRepositoryInterface, PlanRepositoryInterface
    
    # Import Elasticsearch interfaces
    from ..repo.es.interfaces import (
        ESPOIRepositoryInterface,
        ESAutocompleteRepositoryInterface
    )
    
    # Import Autocomplete interfaces
    from ..repo.mongo.interfaces import AutocompleteRepositoryInterface

    # Import PostgreSQL repository implementations
    from ..repo.postgre.implementations.user_repository import UserRepository
    from ..repo.postgre.implementations.token_repository import TokenRepository
    from ..repo.postgre.implementations.role_repository import RoleRepository, UserRoleRepository
    from ..repo.postgre.implementations.cost_usage_repository import CostUsageRepository
    
    # Import MongoDB repository implementations
    from ..repo.mongo.poi_repository import POIRepository
    from ..repo.mongo.plan_repository import PlanRepository
    
    # Import Elasticsearch repository implementations
    from ..repo.es.es_poi_repository import ESPOIRepository
    from ..repo.es.es_autocomplete_repository import ESAutocompleteRepository
    
    # Import MongoDB Autocomplete repository
    from ..repo.mongo.autocomplete_repository import AutocompleteRepository

    from ..utils.firebase_interface import FirebaseInterface
    from ..utils.firebase_helper import FirebaseHelper

    # Import services
    from ..service.user_service import UserService
    from ..service.edit_service import EditService
    from ..service.auth_service import AuthService
    from ..service.cost_usage_service import CostUsageService
    from ..service.places_service import PlacesService
    from ..service.search_service import SearchService
    from ..service.planner_service import PlannerService  # Week 4
    from ..service.autocomplete_service import AutocompleteService  # Hybrid Autocomplete v2
    
    container = DIContainer.get_instance()
    
    # Register PostgreSQL repository implementations
    container.register(UserInterface.__name__, UserRepository())
    container.register(TokenInterface.__name__, TokenRepository())
    container.register(RoleInterface.__name__, RoleRepository())
    container.register(UserRoleInterface.__name__, UserRoleRepository())
    container.register(CostUsageInterface.__name__, CostUsageRepository())
    
    # Register MongoDB repository implementations
    container.register(POIRepositoryInterface.__name__, POIRepository())
    container.register(PlanRepositoryInterface.__name__, PlanRepository())
    
    # Register Elasticsearch repository implementations
    container.register(ESPOIRepositoryInterface.__name__, ESPOIRepository())
    container.register(ESAutocompleteRepositoryInterface.__name__, ESAutocompleteRepository())
    
    # Register MongoDB Autocomplete repository
    container.register(AutocompleteRepositoryInterface.__name__, AutocompleteRepository())
    
    # Register Firebase helper
    container.register(FirebaseInterface.__name__, FirebaseHelper())
    
    # Register services with factory functions for proper DI
    def create_auth_service(container):
        token_repo = container.resolve(TokenInterface.__name__)
        user_repo = container.resolve(UserInterface.__name__)
        role_repo = container.resolve(RoleInterface.__name__)
        user_role_repo = container.resolve(UserRoleInterface.__name__)
        return AuthService(token_repo, user_repo, role_repo, user_role_repo)
    
    def create_user_service(container):
        user_repo = container.resolve(UserInterface.__name__)
        return UserService(user_repo)
    
    def create_edit_service(container):
        user_repo = container.resolve(UserInterface.__name__)
        firebase_helper = container.resolve(FirebaseInterface.__name__)
        return EditService(user_repo, firebase_helper)
    
    def create_cost_usage_service(container):
        cost_usage_repo = container.resolve(CostUsageInterface.__name__)
        return CostUsageService(cost_usage_repo)
    
    def create_places_service(container):
        poi_repo = container.resolve(POIRepositoryInterface.__name__)
        es_repo = container.resolve(ESPOIRepositoryInterface.__name__)
        cost_usage_repo = container.resolve(CostUsageInterface.__name__)
        return PlacesService(poi_repo, es_repo, cost_usage_repo)
    
    def create_search_service(container):
        poi_repo = container.resolve(POIRepositoryInterface.__name__)
        es_repo = container.resolve(ESPOIRepositoryInterface.__name__)
        return SearchService(
            poi_repo=poi_repo,
            es_repo=es_repo
        )
    
    def create_planner_service(container):
        plan_repo = container.resolve(PlanRepositoryInterface.__name__)
        cost_usage_service = container.resolve(CostUsageService.__name__)
        return PlannerService(plan_repo, cost_usage_service)
    
    def create_autocomplete_service(container):
        """Create AutocompleteService with ES, MongoDB, and Google provider."""
        from ..providers.places.google_places_provider import GooglePlacesProvider
        
        es_repo = container.resolve(ESAutocompleteRepositoryInterface.__name__)
        mongo_repo = container.resolve(AutocompleteRepositoryInterface.__name__)
        google_provider = GooglePlacesProvider()
        
        return AutocompleteService(
            es_repo=es_repo,
            mongo_repo=mongo_repo,
            google_provider=google_provider
        )
    
    container.register(AuthService.__name__, create_auth_service)
    container.register(UserService.__name__, create_user_service)
    container.register(EditService.__name__, create_edit_service)
    container.register(CostUsageService.__name__, create_cost_usage_service)
    container.register(PlacesService.__name__, create_places_service)
    container.register(SearchService.__name__, create_search_service)
    container.register(PlannerService.__name__, create_planner_service)  # Week 4
    container.register(AutocompleteService.__name__, create_autocomplete_service)  # Hybrid Autocomplete v2

    _is_initialized = True
    return container

# Initialize the dependency injection system
def init_di():
    """Initialize the dependency injection system.
    Call this function from your application's entry point."""
    return setup_dependencies()
