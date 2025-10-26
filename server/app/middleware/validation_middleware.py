"""
Validation middleware for Flask request data validation.
"""
from functools import wraps

from flask import request, jsonify
from validate_email_address import validate_email as validate_email_address


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


def get_json_or_error(request):
    """
    Get JSON from request or return error response.
    
    Args:
        request: Flask request object
    
    Returns:
        tuple: (data, error_response) where error_response is None if successful
    """
    data = request.get_json()
    if data is None:
        return None, (jsonify({
            "resultMessage": {
                "en": "Invalid JSON data.",
                "vn": "Dữ liệu JSON không hợp lệ."
            },
            "resultCode": "00004"
        }), 400)
    return data, None


def validate_required_fields(data, required_fields):
    """
    Validate that all required fields are present and not None/empty.
    
    Args:
        data: dict with request data
        required_fields: list/set of required field names
        
    Returns:
        error_response or None if validation passes
    """
    if isinstance(required_fields, (list, tuple)):
        missing_fields = [field for field in required_fields if data.get(field) is None]
    else:  # set
        missing_fields = {field for field in required_fields if data.get(field) is None}
    
    if missing_fields:
        return jsonify({
            "resultMessage": {
                "en": "Please provide all required fields!",
                "vn": "Vui lòng cung cấp tất cả các trường bắt buộc!"
            },
            "resultCode": "00025"
        }), 400
    return None


def validate_email(email):
    """
    Validate email format.
    
    Args:
        email: email string to validate
        
    Returns:
        error_response or None if validation passes
    """
    if not validate_email_address(email):
        return jsonify({
            "resultMessage": {
                "en": "Please provide a valid email address!",
                "vn": "Vui lòng cung cấp một địa chỉ email hợp lệ!"
            },
            "resultCode": "00026"
        }), 400
    return None
