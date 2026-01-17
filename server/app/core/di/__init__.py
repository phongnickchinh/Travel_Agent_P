"""
Dependency Injection Package
============================

Contains DI container and setup for dependency injection.

Classes:
- DIContainer: Singleton container for dependency management

Functions:
- init_di: Initialize all dependencies
- setup_dependencies: Register all repos and services

Author: Travel Agent P Team
"""

from .di_container import DIContainer
from .di_setup import init_di, setup_dependencies

__all__ = [
    "DIContainer",
    "init_di",
    "setup_dependencies",
]
