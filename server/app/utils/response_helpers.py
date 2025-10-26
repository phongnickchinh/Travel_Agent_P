"""
Response helper functions.

Pure utility functions for building standardized API responses.
These functions don't depend on Flask request context and can be used anywhere.
"""
from flask import jsonify


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
        
    Example:
        return build_error_response(
            "Invalid email format",
            "Định dạng email không hợp lệ",
            "INVALID_EMAIL",
            400
        )
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
        
    Example:
        return build_success_response(
            "Login successful",
            "Đăng nhập thành công",
            "LOGIN_SUCCESS",
            data={"access_token": token, "user": user_data},
            200
        )
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
