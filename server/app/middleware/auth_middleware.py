"""
Authentication middleware for JWT token validation.
"""
from functools import wraps
from inspect import signature
import jwt

from flask import request, jsonify

from config import secret_key
from ..core.di_container import DIContainer
from ..repo.user_interface import UserInterface


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


def JWT_required(f):
    """Decorator to require JSON Web Token for API access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return _build_no_token_response()
        
        auth_header_parts = auth_header.split(" ")
        if len(auth_header_parts) != 2 or not auth_header_parts[1]:
            return _build_no_token_response()
            
        token = auth_header_parts[1]
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return _build_token_error_response()
        except jwt.InvalidTokenError:
            return _build_token_error_response()
            
        user_id = payload.get("user_id")
        if not user_id:
            return _build_token_error_response()
            
        # Use DI container instead of direct instantiation
        container = DIContainer.get_instance()
        user_repo = container.resolve(UserInterface.__name__)
        user = user_repo.get_user_by_id(user_id)
        if not user:
            return _build_token_error_response()
            
        func_signature = signature(f)
        if "user_id" in func_signature.parameters:
            return f(user_id, *args, **kwargs)
        elif "user" in func_signature.parameters:
            return f(user, *args, **kwargs)
        
        return f(*args, **kwargs)

    return decorated_function
