"""
Autocomplete Controller Package
Flask Blueprint for Hybrid Autocomplete v2 endpoints
"""

from flask import Blueprint

autocomplete_bp = Blueprint("autocomplete_v2", __name__, url_prefix="/v2/autocomplete")


def init_app():
    """Initialize Autocomplete v2 controller."""
    from .autocomplete_controller import init_autocomplete_controller
    init_autocomplete_controller()
    return autocomplete_bp


# Import controller after blueprint is defined
from . import autocomplete_controller
