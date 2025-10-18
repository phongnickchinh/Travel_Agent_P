from flask import Blueprint

auth_api = Blueprint("auth_api", __name__)
def init_app():
    """Initialize all controllers for the AuthService."""
    from .auth_controller import init_auth_controller
    init_auth_controller()
    return auth_api

# Import controllers after blueprint is defined
from . import auth_controller