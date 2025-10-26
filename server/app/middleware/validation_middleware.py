"""
Validation middleware for Flask request data validation.
"""
from functools import wraps

from flask import request, jsonify


def validate_fields(allow_fields):
    """Decorator to validate fields in request JSON data."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            data = request.get_json() or {}

            missing_fields = {field for field in allow_fields if not data.get(field)}
            if missing_fields:
                return jsonify({
                    "resultMessage": {
                        "en": "Please provide all required fields!",
                        "vn": "Vui lòng cung đầy đủ các trường bắt buộc!"
                    },
                    "resultCode": "00099"
                }), 400

            return func(*args, **kwargs)
        return wrapper
    return decorator
