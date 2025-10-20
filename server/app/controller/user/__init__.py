from flask import Blueprint

# Define the blueprint first
user_api = Blueprint("user_api", __name__)

def init_app():
    """Initialize all controllers for the user service."""
    from .user_controller import init_user_controller
    from .edit_controller import init_edit_controller
    
    # Initialize all controllers
    init_user_controller()
    init_edit_controller()
    
    return user_api

# Import controllers after blueprint is defined, but don't initialize them yet
from . import user_controller, edit_controller

