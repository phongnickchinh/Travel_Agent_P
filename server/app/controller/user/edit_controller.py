from flask import request, jsonify

from . import user_api
from ...service.edit_service import EditService
from ...service.auth_service import AuthService
from ...utils.middleware import JWT_required
from ...utils.validation_helpers import (
    get_json_or_error,
    validate_required_fields,
    build_error_response,
    build_success_response
)
from ...core.di_container import DIContainer


class EditController:
    def __init__(self, edit_service: EditService, auth_service: AuthService):
        self.edit_service = edit_service
        self.auth_service = auth_service
        self._register_routes()
    
    def _register_routes(self):
        """Register all routes with Flask."""
        user_api.add_url_rule("/change-password", "change_password", 
                             self._wrap_jwt_required(self.change_password), methods=["POST"])
        user_api.add_url_rule("/", "edit_user", 
                             self._wrap_jwt_required(self.edit_user), methods=["PUT"])
    
    def _wrap_jwt_required(self, f):
        """Helper to maintain JWT required middleware while using class methods."""
        @JWT_required
        def wrapper(user):
            return f(user)
        return wrapper
    
    def change_password(self, user):
        data, error = get_json_or_error(request)
        if error:
            return error
        
        error = validate_required_fields(data, ["oldPassword", "newPassword"])
        if error:
            return error
            
        old_password = data.get("oldPassword")
        new_password = data.get("newPassword")
            
        if old_password == new_password:
            return build_error_response(
                "Your new password should not be the same as your old password, please try another password.",
                "Mật khẩu mới của bạn không nên giống với mật khẩu cũ, vui lòng thử một mật khẩu khác.",
                "00073"
            )
            
        if not self.auth_service.validate_password(new_password):
            return build_error_response(
                "Please provide both old and new passwords longer than 6 characters and shorter than 20 characters.",
                "Vui lòng cung cấp mật khẩu cũ và mới dài hơn 6 ký tự và ngắn hơn 20 ký tự.",
                "00069"
            )
            
        if not self.edit_service.verify_old_password(user, old_password):
            return build_error_response(
                "Your old password does not match the password you entered, please enter the correct password.",
                "Mật khẩu cũ của bạn không khớp với mật khẩu bạn nhập, vui lòng nhập mật khẩu đúng.",
                "00072"
            )
            
        self.edit_service.save_new_password(user, new_password)
        return build_success_response(
            "Your password was changed successfully.",
            "Mật khẩu của bạn đã được thay đổi thành công.",
            "00076"
        )
        
    def edit_user(self, user):
        data = request.form
        avatar_file = request.files.get("image")
        if not data and not avatar_file:
            return build_error_response(
                "No data provided!",
                "Không tìm thấy dữ liệu nào được cung cấp!",
                "00004"
            )
        
        if data:
            ALLOW_FIELDS = {"username", "name", "language", "timezone", "deviceId"}
            unknown_fields = {field for field in data if field not in ALLOW_FIELDS}
            if unknown_fields:
                return build_error_response(
                    f"Unknown fields: {', '.join(unknown_fields)}",
                    f"Các trường không xác định: {', '.join(unknown_fields)}",
                    "00003"
                )
            
        if data.get("username") and self.auth_service.is_duplicated_username(data["username"]):
            return build_error_response(
                "This username is already in use, please choose another username.",
                "Username này đã được sử dụng, vui lòng chọn username khác.",
                "00071"
            )
        
        updated_user = self.edit_service.update_user_info(user, data, avatar_file)
        return build_success_response(
            "Your profile information was changed successfully.",
            "Thông tin hồ sơ của bạn đã được thay đổi thành công.",
            "00086",
            {"updatedUser": updated_user.to_json()}
        )


# Create the controller instance
def init_edit_controller():
    container = DIContainer.get_instance()
    edit_service = container.resolve(EditService.__name__)
    auth_service = container.resolve(AuthService.__name__)
    return EditController(edit_service, auth_service)