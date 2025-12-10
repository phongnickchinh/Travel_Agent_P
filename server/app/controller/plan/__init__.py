"""
Plan Blueprint - User API routes for travel plans
==================================================

Purpose:
- Define Flask blueprint for /api/plan routes
- User-facing endpoints (authentication required)

Author: Travel Agent P Team
Date: Week 4 - HuggingFace + LangChain Integration
"""

from flask import Blueprint

plan_api = Blueprint('plan_api', __name__, url_prefix='/plan')


def init_app():
    """Initialize plan controller and return blueprint."""
    from .plan_controller import init_plan_controller
    init_plan_controller()
    return plan_api
