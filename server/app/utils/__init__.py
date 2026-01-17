"""
Utilities Package
=================

Various utility functions and helpers.

Modules:
- blacklist_cleaner: JWT blacklist cleanup (deprecated, using Redis TTL)
- circuit_breaker: Circuit breaker pattern for external APIs
- cost_meter: API cost tracking decorators
- jwt_helpers: JWT token utilities
- mock_pois: Mock POI data for testing
- poi_dedupe: POI deduplication algorithm
- response_helpers: Response formatting utilities
- retry_backoff: Retry with exponential backoff
- sanitization: Input sanitization utilities
- text_utils: Text processing utilities

Moved to providers/:
- firebase_helper → providers.firebase.firebase_helper
- firebase_interface → providers.firebase.firebase_interface
- google_oauth_helper → providers.google.google_oauth_helper

Author: Travel Agent P Team
"""

# Re-export moved items for backward compatibility
# TODO: Update all imports to use providers.* and remove these re-exports

from ..providers.firebase.firebase_interface import FirebaseInterface
from ..providers.firebase.firebase_helper import FirebaseHelper
from ..providers.google.google_oauth_helper import (
    verify_google_token,
    get_google_user_info,
    generate_username_from_email,
    generate_device_id_for_oauth
)

__all__ = [
    # Backward compatibility re-exports (deprecated, use providers.* instead)
    "FirebaseInterface",
    "FirebaseHelper",
    "verify_google_token",
    "get_google_user_info",
    "generate_username_from_email",
    "generate_device_id_for_oauth",
]
