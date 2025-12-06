"""
Search Controller Package
Flask Blueprint for Elasticsearch search endpoints
"""

from flask import Blueprint

search_bp = Blueprint("search", __name__, url_prefix="/search")

def init_app():
    """Initialize Search controller."""
    from .search_controller import init_search_controller
    init_search_controller()
    return search_bp

# Import controller after blueprint is defined
from . import search_controller
