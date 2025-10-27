"""
Repository Interfaces Package

This package contains all abstract interfaces for data access layer.
Each interface defines the contract that repository implementations must follow.
"""

from .user_repository_interface import UserInterface
from .token_repository_interface import TokenInterface
from .role_repository_interface import RoleInterface, UserRoleInterface

__all__ = [
    'UserInterface',
    'TokenInterface',
    'RoleInterface',
    'UserRoleInterface'
]
