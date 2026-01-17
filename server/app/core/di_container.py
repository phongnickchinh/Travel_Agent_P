"""
Backward Compatibility Shim
===========================

This file provides backward compatibility for imports from `core.di_container`.
The actual implementation has been moved to `core.di.di_container`.

DEPRECATED: Use `from app.core.di import DIContainer` instead.
"""

from .di.di_container import DIContainer

__all__ = ['DIContainer']
