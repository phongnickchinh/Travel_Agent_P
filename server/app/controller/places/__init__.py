"""
Places Controller Package
Flask Blueprint for POI/Places endpoints
"""

from flask import Blueprint

places_bp = Blueprint("places", __name__, url_prefix="/places")

def init_app():
    """Initialize Places controller."""
    from .places_controller import init_places_controller
    init_places_controller()
    return places_bp

# Import controller after blueprint is defined
from . import places_controller
