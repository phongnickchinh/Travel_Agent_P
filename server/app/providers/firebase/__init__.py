"""
Firebase Provider
=================

Firebase Storage integration for image uploads.

Classes:
- FirebaseInterface: Abstract interface for Firebase operations
- FirebaseHelper: Implementation with Firebase Admin SDK

Author: Travel Agent P Team
"""

from .firebase_interface import FirebaseInterface
from .firebase_helper import FirebaseHelper

__all__ = [
    "FirebaseInterface",
    "FirebaseHelper",
]
