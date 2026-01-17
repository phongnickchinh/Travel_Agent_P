from flask import jsonify, request

from . import user_api
from ...service.user_service import UserService
from ...service.edit_service import EditService
from ...middleware import JWT_required
from ...middleware.validation_middleware import get_json_or_error
from ...utils.response_helpers import build_success_response
from ...core.di_container import DIContainer
from ...core.rate_limiter import rate_limit, get_identifier_from_auth_token
from config import Config


class UserController:
    def __init__(self, user_service: UserService, edit_service: EditService):
        self.user_service = user_service
        self.edit_service = edit_service
        self._register_routes()
    
    def _register_routes(self):
        """Register all routes with Flask."""
        user_api.add_url_rule("/", "get_user", self._wrap_jwt_with_rate_limit(self.get_user), methods=["GET"])
        user_api.add_url_rule("/", "update_user", self._wrap_jwt_with_rate_limit(self.update_user), methods=["PUT"])
        user_api.add_url_rule("/avatar", "upload_avatar", self._wrap_jwt_with_avatar_limit(self.upload_avatar), methods=["POST"])
        user_api.add_url_rule("/", "delete_user", self._wrap_jwt_with_rate_limit(self.delete_user), methods=["DELETE"])
    
    def _wrap_jwt_with_rate_limit(self, f):
        """Wrap with JWT required and moderate rate limiting (30/min)."""
        @rate_limit(
            max_requests=Config.RATE_LIMIT_USER,
            window_seconds=Config.RATE_LIMIT_USER_WINDOW,
            identifier_func=get_identifier_from_auth_token,
            key_prefix='user'
        )
        @JWT_required
        def wrapper(user):
            return f(user)
        wrapper.__name__ = f.__name__
        return wrapper
    
    def _wrap_jwt_with_avatar_limit(self, f):
        """Wrap with JWT required and strict rate limiting for avatar upload (5/hour)."""
        @rate_limit(
            max_requests=Config.RATE_LIMIT_AVATAR_UPLOAD,
            window_seconds=Config.RATE_LIMIT_AVATAR_UPLOAD_WINDOW,
            identifier_func=get_identifier_from_auth_token,
            key_prefix='avatar_upload'
        )
        @JWT_required
        def wrapper(user):
            return f(user)
        wrapper.__name__ = f.__name__
        return wrapper
    
    def get_user(self, user):
        return build_success_response(
            "The user information has gotten successfully.",
            "Thông tin người dùng đã được lấy thành công.",
            "00089",
            {"user": user.as_dict(exclude=["password_hash"])}
        )
    
    def update_user(self, user):
        """Update user profile information (username, name, language, timezone)."""
        data, error = get_json_or_error(request)
        if error:
            return error
        
        # Extract allowed fields only
        allowed_fields = ['username', 'name', 'language', 'timezone']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({
                "status": "error",
                "message": "No valid fields to update",
                "message_vi": "Không có trường hợp lệ để cập nhật",
                "code": "00004"
            }), 400
        
        try:
            # Update user via EditService (no image file for JSON requests)
            updated_user = self.edit_service.update_user_info(user, update_data, None)
            
            return build_success_response(
                "Profile updated successfully.",
                "Hồ sơ đã được cập nhật thành công.",
                "00086",
                {"user": updated_user.as_dict(exclude=["password_hash"])}
            )
        except ValueError as e:
            # Username already taken or other validation error
            return jsonify({
                "status": "error",
                "message": str(e),
                "message_vi": str(e),
                "code": "00071"
            }), 400
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e),
                "message_vi": "Có lỗi xảy ra khi cập nhật hồ sơ",
                "code": "00001"
            }), 500
    
    def upload_avatar(self, user):
        """Upload user avatar image."""
        if 'image' not in request.files:
            return jsonify({
                "status": "error",
                "message": "No image file provided",
                "message_vi": "Không có file ảnh",
                "code": "00004"
            }), 400
        
        image_file = request.files['image']
        
        if image_file.filename == '':
            return jsonify({
                "status": "error",
                "message": "No file selected",
                "message_vi": "Không có file được chọn",
                "code": "00004"
            }), 400
        
        try:
            # Update user with avatar via EditService
            updated_user = self.edit_service.update_user_info(user, {}, image_file)
            
            return build_success_response(
                "Avatar uploaded successfully.",
                "Ảnh đại diện đã được tải lên thành công.",
                "00086",
                {"user": updated_user.as_dict(exclude=["password_hash"])}
            )
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e),
                "message_vi": "Có lỗi xảy ra khi tải lên ảnh đại diện",
                "code": "00001"
            }), 500
    
    def delete_user(self, user):
        self.user_service.delete_user_account(user)
        return build_success_response(
            "The user account has been deleted successfully.",
            "Tài khoản người dùng đã được xóa thành công.",
            "00092"
        )


# Create the controller instance
def init_user_controller():
    container = DIContainer.get_instance()
    user_service = container.resolve(UserService.__name__)
    edit_service = container.resolve(EditService.__name__)
    return UserController(user_service, edit_service)