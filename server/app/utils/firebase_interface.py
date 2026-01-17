"""
Backward Compatibility Shim
===========================

DEPRECATED: This file has been moved to providers.firebase.firebase_interface
Use: from app.providers.firebase import FirebaseInterface
"""

from ..providers.firebase.firebase_interface import FirebaseInterface

__all__ = ['FirebaseInterface']
