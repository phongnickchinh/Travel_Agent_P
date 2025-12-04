"""
Admin Authentication Middleware
================================

Purpose:
- Verify user has admin role
- Protect admin-only endpoints (PlacesController, etc.)
- Used with @admin_required decorator

Author: Travel Agent P Team
Date: December 4, 2025
"""

from functools import wraps
from inspect import signature
import jwt
import logging

from flask import request, jsonify

from config import secret_key
from ..core.di_container import DIContainer
from ..repo.postgre.interfaces.user_repository_interface import UserInterface
from ..cache.redis_blacklist import RedisBlacklist

logger = logging.getLogger(__name__)


def _build_admin_required_response():
    """Helper to build admin access denied response."""
    return jsonify({
        "resultMessage": {
            "en": "Access denied. Admin privileges required.",
            "vn": "Truy cập bị từ chối. Yêu cầu quyền quản trị viên."
        },
        "resultCode": "ADMIN_REQUIRED"
    }), 403


def _build_token_error_response():
    """Helper to build standardized token error response."""
    return jsonify({
        "resultMessage": {
            "en": "Invalid token.",
            "vn": "Token không hợp lệ. Token có thể đã hết hạn."
        },
        "resultCode": "00012"
    }), 401


def _build_no_token_response():
    """Helper to build standardized no token provided response."""
    return jsonify({
        "resultMessage": {
            "en": "Access denied. No token provided.",
            "vn": "Truy cập bị từ chối. Không có token được cung cấp."
        },
        "resultCode": "00006"
    }), 401


def admin_required(f):
    """
    Decorator to require admin role for API access.
    
    Usage:
        @admin_required
        def some_admin_endpoint(user_id):
            # Only admins can access this
            pass
    
    Checks:
    1. Valid JWT token
    2. Token not blacklisted
    3. User exists
    4. User has 'admin' role
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return _build_no_token_response()
        
        auth_header_parts = auth_header.split(" ")
        if len(auth_header_parts) != 2 or not auth_header_parts[1]:
            return _build_no_token_response()
            
        token = auth_header_parts[1]
        
        # Check 1: Verify token is not blacklisted
        if RedisBlacklist.is_blacklisted(token):
            logger.warning("⚠️ Attempted admin access with blacklisted token")
            return _build_token_error_response()
        
        # Check 2: Decode and validate JWT
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return _build_token_error_response()
        except jwt.InvalidTokenError:
            return _build_token_error_response()
            
        user_id = payload.get("user_id")
        if not user_id:
            return _build_token_error_response()
        
        # Check 3: Get user from database
        container = DIContainer.get_instance()
        user_repo = container.resolve(UserInterface.__name__)
        user = user_repo.get_user_by_id(user_id)
        
        if not user:
            return _build_token_error_response()
        
        # Check 4: Verify admin role
        user_roles = [role.role_name for role in user.roles]
        
        if 'admin' not in user_roles:
            logger.warning(f"⚠️ User {user_id} ({user.email}) attempted admin access without admin role (roles: {user_roles})")
            return _build_admin_required_response()
        
        logger.info(f"✅ Admin access granted: {user.email}")
        
        # Call original function with user_id or user object
        func_signature = signature(f)
        if "user_id" in func_signature.parameters:
            return f(user_id, *args, **kwargs)
        elif "user" in func_signature.parameters:
            return f(user, *args, **kwargs)
        
        return f(*args, **kwargs)

    return decorated_function
