"""Validation helper functions for request data."""
from flask import jsonify
from validate_email_address import validate_email as validate_email_address


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


def build_error_response(message_en, message_vn, result_code, status_code=400):
    """
    Build standardized error response.
    
    Args:
        message_en: English error message
        message_vn: Vietnamese error message
        result_code: Application result code
        status_code: HTTP status code (default 400)
        
    Returns:
        tuple: (json_response, status_code)
    """
    return jsonify({
        "resultMessage": {
            "en": message_en,
            "vn": message_vn
        },
        "resultCode": result_code
    }), status_code


def build_success_response(message_en, message_vn, result_code, data=None, status_code=200):
    """
    Build standardized success response.
    
    Args:
        message_en: English success message
        message_vn: Vietnamese success message
        result_code: Application result code
        data: Optional dict with additional response data
        status_code: HTTP status code (default 200)
        
    Returns:
        tuple: (json_response, status_code)
    """
    response = {
        "resultMessage": {
            "en": message_en,
            "vn": message_vn
        },
        "resultCode": result_code
    }
    if data:
        response.update(data)
    return jsonify(response), status_code
