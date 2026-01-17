"""
Google OAuth Provider
=====================

Google OAuth 2.0 integration for authentication.

Functions:
- verify_google_token: Verify Google ID token
- get_google_user_info: Get user info from access token

Author: Travel Agent P Team
"""

from .google_oauth_helper import verify_google_token, get_google_user_info

__all__ = [
    "verify_google_token",
    "get_google_user_info",
]
