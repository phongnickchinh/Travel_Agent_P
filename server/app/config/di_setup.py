
from ..core.di_container import DIContainer

_is_initialized = False

def setup_dependencies():
    """Register all dependencies in the container."""
    global _is_initialized
    
    if _is_initialized:
        return
    
    # Import interfaces
    from ..repo.postgre.interfaces.user_repository_interface import UserInterface
    from ..repo.postgre.interfaces.token_repository_interface import TokenInterface
    from ..repo.postgre.interfaces.role_repository_interface import RoleInterface, UserRoleInterface
    from ..repo.postgre.interfaces.cost_usage_interface import CostUsageInterface

    # Import repository implementations
    from ..repo.postgre.implementations.user_repository import UserRepository
    from ..repo.postgre.implementations.token_repository import TokenRepository
    from ..repo.postgre.implementations.role_repository import RoleRepository, UserRoleRepository
    from ..repo.postgre.implementations.cost_usage_repository import CostUsageRepository

    from ..utils.firebase_interface import FirebaseInterface
    from ..utils.firebase_helper import FirebaseHelper

    # Import services
    from ..service.user_service import UserService
    from ..service.edit_service import EditService
    from ..service.auth_service import AuthService
    from ..service.cost_usage_service import CostUsageService
    
    container = DIContainer.get_instance()
    
    # Register repository implementations
    container.register(UserInterface.__name__, UserRepository())
    container.register(TokenInterface.__name__, TokenRepository())
    container.register(RoleInterface.__name__, RoleRepository())
    container.register(UserRoleInterface.__name__, UserRoleRepository())
    container.register(CostUsageInterface.__name__, CostUsageRepository())
    
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
    
    container.register(AuthService.__name__, create_auth_service)
    container.register(UserService.__name__, create_user_service)
    container.register(EditService.__name__, create_edit_service)
    container.register(CostUsageService.__name__, create_cost_usage_service)

    _is_initialized = True
    return container

# Initialize the dependency injection system
def init_di():
    """Initialize the dependency injection system.
    Call this function from your application's entry point."""
    return setup_dependencies()
