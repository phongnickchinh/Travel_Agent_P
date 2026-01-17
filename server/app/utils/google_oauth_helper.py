"""
Backward Compatibility Shim
===========================

DEPRECATED: This file has been moved to providers.google.google_oauth_helper
Use: from app.providers.google import verify_google_token, get_google_user_info
"""

from ..providers.google.google_oauth_helper import (
    verify_google_token,
    get_google_user_info,
    generate_username_from_email,
    generate_device_id_for_oauth
)

__all__ = [
    'verify_google_token',
    'get_google_user_info',
    'generate_username_from_email',
    'generate_device_id_for_oauth'
]
