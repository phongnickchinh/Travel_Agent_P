"""
Providers Package - External Service Integrations
==================================================

Submodules:
- llm/: Language Model adapters (Groq, HuggingFace)
- places/: Location data providers (Google Places)
- firebase/: Firebase Storage integration
- google/: Google OAuth integration

Author: Travel Agent P Team
"""

from .base_provider import BaseProvider
from .places.google_places_provider import GooglePlacesProvider
from .firebase import FirebaseInterface, FirebaseHelper
from .google import verify_google_token, get_google_user_info

__all__ = [
    'BaseProvider', 
    'GooglePlacesProvider',
    'FirebaseInterface',
    'FirebaseHelper',
    'verify_google_token',
    'get_google_user_info',
]
