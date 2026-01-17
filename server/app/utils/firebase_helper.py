"""
Backward Compatibility Shim
===========================

DEPRECATED: This file has been moved to providers.firebase.firebase_helper
Use: from app.providers.firebase import FirebaseHelper
"""

from ..providers.firebase.firebase_helper import FirebaseHelper

__all__ = ['FirebaseHelper']
