"""
Common Module
==============

Shared utilities and configurations:
- Error handlers
- Logging configuration
"""

from .errors import handle_exception
from .logging_config import setup_logging

__all__ = [
    'handle_exception',
    'setup_logging'
]
