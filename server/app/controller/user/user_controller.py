from flask import jsonify

from . import user_api
from ...service.user_service import UserService
from ...middleware import JWT_required
from ...utils.validation_helpers import build_success_response
from ...core.di_container import DIContainer


class UserController:
    def __init__(self, user_service: UserService):
        self.user_service = user_service
        self._register_routes()
    
    def _register_routes(self):
        """Register all routes with Flask."""
        user_api.add_url_rule("/", "get_user", self._wrap_jwt_required(self.get_user), methods=["GET"])
        user_api.add_url_rule("/", "delete_user", self._wrap_jwt_required(self.delete_user), methods=["DELETE"])
    
    def _wrap_jwt_required(self, f):
        """Helper to maintain JWT required middleware while using class methods."""
        @JWT_required
        def wrapper(user):
            return f(user)
        return wrapper
    
    def get_user(self, user):
        return build_success_response(
            "The user information has gotten successfully.",
            "Thông tin người dùng đã được lấy thành công.",
            "00089",
            {"user": user.as_dict(exclude=["password_hash"])}
        )
    
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
    return UserController(user_service)