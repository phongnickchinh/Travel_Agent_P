"""
Admin Authentication Controller
================================

Purpose:
- Admin-only login and registration
- Separate from regular user authentication
- Used for accessing admin endpoints (PlacesController, etc.)

Endpoints:
- POST /api/admin/auth/login - Admin login
- POST /api/admin/auth/register - Create admin account (protected)

Author: Travel Agent P Team
Date: December 4, 2025
"""

from flask import request, jsonify
import logging

from . import admin_bp
from ...service.auth_service import AuthService
from ...middleware import admin_required
from ...utils.response_helpers import (
    build_error_response,
    build_success_response
)
from ...core.di_container import DIContainer
from ...core.rate_limiter import rate_limit, get_identifier_by_email
from config import Config

logger = logging.getLogger(__name__)


class AdminController:
    """
    Admin Authentication Controller
    
    Simple admin login/register with username + password
    No email verification required for admins
    """
    
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
        self._register_routes()
        logger.info("[INFO] AdminController initialized")
    
    def _register_routes(self):
        """Register admin auth routes."""
        admin_bp.add_url_rule("/login", "admin_login", self.login, methods=["POST"])
        admin_bp.add_url_rule("/register", "admin_register", admin_required(self.register), methods=["POST"])
    
    def login(self):
        """
        Admin login endpoint.
        
        Request Body:
            {
                "username": "admin",  // or email
                "password": "your_password"
            }
        
        Response Success (200):
            {
                "resultMessage": {"en": "...", "vn": "..."},
                "resultCode": "ADMIN_LOGIN_SUCCESS",
                "data": {
                    "user": {...},
                    "role": "admin",
                    "access_token": "...",
                    "refresh_token": "..."
                }
            }
        
        Response Error (401):
            {
                "resultMessage": {"en": "...", "vn": "..."},
                "resultCode": "INVALID_CREDENTIALS"
            }
        
        Example:
            POST /api/admin/auth/login
            Body: {
                "username": "admin",
                "password": "Admin@123"
            }
        """
        @rate_limit(
            max_requests=Config.RATE_LIMIT_LOGIN,
            window_seconds=Config.RATE_LIMIT_LOGIN_WINDOW,
            identifier_func=lambda: request.json.get('username', request.remote_addr),
            key_prefix='admin_login'
        )
        def _login_handler():
            try:
                data = request.get_json()
                
                if not data:
                    return build_error_response(
                        "Request body is required",
                        "Yêu cầu phải có body",
                        "MISSING_BODY",
                        400
                    )
                
                username = data.get('username', '').strip()
                password = data.get('password', '')
                
                if not username or not password:
                    return build_error_response(
                        "Username and password are required",
                        "Tên đăng nhập và mật khẩu là bắt buộc",
                        "MISSING_CREDENTIALS",
                        400
                    )
                
                # Try login by username or email
                user, role, verification_status = self.auth_service.validate_login(username, password)
                
                # Check if user has admin role
                if not user:
                    return build_error_response(
                        "Invalid credentials",
                        "Thông tin đăng nhập không đúng",
                        "INVALID_CREDENTIALS",
                        401
                    )
                
                # Check admin role
                user_roles = [r.role_name for r in user.roles]
                if 'admin' not in user_roles:
                    logger.warning(f"[ADMIN] Non-admin user {username} attempted admin login")
                    return build_error_response(
                        "Access denied. Admin privileges required.",
                        "Truy cập bị từ chối. Yêu cầu quyền quản trị viên.",
                        "ADMIN_REQUIRED",
                        403
                    )
                
                # Generate tokens
                access_token, refresh_token = self.auth_service.generate_tokens(user.id)
                
                logger.info(f"[ADMIN] Admin login successful: {user.email or user.username}")
                
                return build_success_response(
                    "Admin login successful",
                    "Đăng nhập admin thành công",
                    "ADMIN_LOGIN_SUCCESS",
                    data={
                        "user": {
                            "id": user.id,
                            "email": user.email,
                            "username": user.username,
                            "name": user.name,
                            "roles": user_roles
                        },
                        "role": "admin",
                        "access_token": access_token,
                        "refresh_token": refresh_token
                    },
                    status_code=200
                )
            
            except Exception as e:
                logger.error(f"[ERROR] Admin login failed: {e}", exc_info=True)
                return build_error_response(
                    "An error occurred during login",
                    "Đã xảy ra lỗi khi đăng nhập",
                    "LOGIN_ERROR",
                    500
                )
        
        return _login_handler()
    
    def register(self, user_id):
        """
        Create new admin account (admin-only).
        
        PROTECTED: Only existing admins can create new admin accounts
        
        Request Body:
            {
                "username": "new_admin",
                "email": "admin@example.com",  // optional
                "password": "Strong@Pass123",
                "name": "Admin Name"  // optional
            }
        
        Response Success (201):
            {
                "resultMessage": {"en": "...", "vn": "..."},
                "resultCode": "ADMIN_CREATED",
                "data": {
                    "user": {...}
                }
            }
        
        Example:
            POST /api/admin/auth/register
            Headers: Authorization: Bearer {admin_token}
            Body: {
                "username": "new_admin",
                "password": "Admin@456",
                "email": "admin2@example.com"
            }
        """
        try:
            data = request.get_json()
            
            if not data:
                return build_error_response(
                    "Request body is required",
                    "Yêu cầu phải có body",
                    "MISSING_BODY",
                    400
                )
            
            username = data.get('username', '').strip()
            password = data.get('password', '')
            email = data.get('email', '').strip()
            name = data.get('name', '').strip()
            
            if not username or not password:
                return build_error_response(
                    "Username and password are required",
                    "Tên đăng nhập và mật khẩu là bắt buộc",
                    "MISSING_CREDENTIALS",
                    400
                )
            
            # Password validation
            if len(password) < 8:
                return build_error_response(
                    "Password must be at least 8 characters",
                    "Mật khẩu phải có ít nhất 8 ký tự",
                    "WEAK_PASSWORD",
                    400
                )
            
            # Create admin user
            new_admin = self.auth_service.create_admin_user(
                username=username,
                password=password,
                email=email if email else None,
                name=name if name else username
            )
            
            if not new_admin:
                return build_error_response(
                    "Failed to create admin account. Username or email may already exist.",
                    "Không thể tạo tài khoản admin. Tên đăng nhập hoặc email có thể đã tồn tại.",
                    "ADMIN_CREATION_FAILED",
                    400
                )
            
            logger.info(f"[ADMIN] New admin created: {new_admin.username} by {user_id}")
            
            return build_success_response(
                "Admin account created successfully",
                "Tạo tài khoản admin thành công",
                "ADMIN_CREATED",
                data={
                    "user": {
                        "id": new_admin.id,
                        "username": new_admin.username,
                        "email": new_admin.email,
                        "name": new_admin.name,
                        "roles": [r.role_name for r in new_admin.roles]
                    }
                },
                status_code=201
            )
        
        except Exception as e:
            logger.error(f"[ERROR] Admin registration failed: {e}", exc_info=True)
            return build_error_response(
                "An error occurred while creating admin account",
                "Đã xảy ra lỗi khi tạo tài khoản admin",
                "REGISTRATION_ERROR",
                500
            )


# Initialize controller with DI
def init_admin_controller():
    """Initialize Admin controller with dependency injection."""
    container = DIContainer.get_instance()
    auth_service = container.resolve('AuthService')
    return AdminController(auth_service)
