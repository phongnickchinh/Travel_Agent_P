"""
Admin Controller Package
Flask Blueprint for admin authentication endpoints
"""

from flask import Blueprint

admin_bp = Blueprint("admin", __name__, url_prefix="/")

def init_app():
    """Initialize Admin controller."""
    from .admin_controller import init_admin_controller
    init_admin_controller()
    return admin_bp

# Import controller after blueprint is defined
from . import admin_controller
