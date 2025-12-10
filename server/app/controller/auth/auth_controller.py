from flask import request, jsonify
import logging

from . import auth_api
from ...service.auth_service import AuthService
from ...tasks.email_tasks import send_email
from ...middleware import (
    JWT_required,
    get_json_or_error,
    validate_required_fields,
    validate_email
)
from ...utils.response_helpers import (
    build_error_response,
    build_success_response
)
from ...core.di_container import DIContainer
from ...core.rate_limiter import rate_limit, get_identifier_by_email
from config import Config


class AuthController:
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
        self._register_routes()
    
    def _register_routes(self):
        """Register all routes with Flask."""
        auth_api.add_url_rule("/config", "auth_config", self.get_auth_config, methods=["GET"])
        auth_api.add_url_rule("/login", "login", self.login, methods=["POST"])
        auth_api.add_url_rule("/google", "google_login", self.google_login, methods=["POST"])
        auth_api.add_url_rule("/link-google", "link_google", self._wrap_jwt_required(self.link_google), methods=["POST"])
        auth_api.add_url_rule("/refresh-token", "refresh_token", self.refresh_token, methods=["POST"])
        auth_api.add_url_rule("/logout", "logout", self._wrap_jwt_required(self.logout), methods=["POST"])
        auth_api.add_url_rule("/register", "register", self.register, methods=["POST"])
        auth_api.add_url_rule("/send-verification-code", "send_verification_code", self.send_verification_code, methods=["POST"])
        auth_api.add_url_rule("/verify-email", "verify_email", self.verify_email, methods=["POST"])
        auth_api.add_url_rule("/request-reset-password", "request_reset_password", self.request_reset_password, methods=["POST"])
        auth_api.add_url_rule("/validate-reset-code", "validate_reset_code", self.validate_reset_code, methods=["POST"])
        auth_api.add_url_rule("/reset-password", "reset_password", self.reset_password, methods=["POST"])
    
    def _wrap_jwt_required(self, f):
        """Helper to maintain JWT required middleware while using class methods."""
        @JWT_required
        def wrapper(user_id):
            return f(user_id)
        return wrapper
    
    def get_auth_config(self):
        """Public endpoint to get authentication configuration (e.g., Google Client ID)."""
        print(Config.GOOGLE_CLIENT_ID)
        return build_success_response(
            "Authentication configuration retrieved successfully.",
            "Lấy cấu hình xác thực thành công.",
            "00100",
            {
                "google_client_id": Config.GOOGLE_CLIENT_ID
            }
        )
    
    def login(self):
        @rate_limit(
            max_requests=Config.RATE_LIMIT_LOGIN,
            window_seconds=Config.RATE_LIMIT_LOGIN_WINDOW,
            identifier_func=get_identifier_by_email,
            key_prefix='login'
        )
        def _login_handler():
            data, error = get_json_or_error(request)
            if error:
                return error
            
            error = validate_required_fields(data, ["email", "password"])
            if error:
                return error
                
            error = validate_email(data["email"])
            if error:
                return error

            user, role, verification_status = self.auth_service.validate_login(data["email"], data["password"])
            
            if verification_status == "NOT_VERIFIED":
                return build_error_response(
                    "Please verify your email before logging in. Check your inbox for the verification code.",
                    "Vui lòng xác minh email của bạn trước khi đăng nhập. Kiểm tra hộp thư để lấy mã xác minh.",
                    "EMAIL_NOT_VERIFIED",
                    403
                )
            
            if not user:
                return build_error_response(
                    "You have entered an invalid email or password.",
                    "Bạn đã nhập một email hoặc mật khẩu không hợp lệ.",
                    "00045"
                )
                
            access_token = self.auth_service.generate_access_token(user.id)
            refresh_token = self.auth_service.generate_refresh_token(user.id)

            return build_success_response(
                "You have successfully logged in.",
                "Bạn đã đăng nhập thành công.",
                "00047",
                {
                    "user": user.as_dict(exclude=["password_hash"]),
                    "role": role,
                    "access_token": access_token,
                    "refresh_token": refresh_token
                }
            )
        
        return _login_handler()
    
    def google_login(self):
        """Handle Google OAuth login."""
        data, error = get_json_or_error(request)
        if error:
            return error
        
        error = validate_required_fields(data, ["token"])
        if error:
            return error
        
        try:
            user, tokens, role = self.auth_service.authenticate_google_user(data["token"])
            
            if not user:
                return build_error_response(
                    "Google authentication failed. Please try again.",
                    "Xác thực Google thất bại. Vui lòng thử lại.",
                    "00090"
                )
            
            access_token, refresh_token = tokens
            
            return build_success_response(
                "You have successfully logged in with Google.",
                "Bạn đã đăng nhập thành công bằng Google.",
                "00091",
                {
                    "user": user.as_dict(exclude=["password_hash"]),
                    "role": role,
                    "access_token": access_token,
                    "refresh_token": refresh_token
                }
            )
        except Exception as e:
            return build_error_response(
                "An error occurred during Google authentication.",
                "Đã xảy ra lỗi trong quá trình xác thực Google.",
                "00092"
            )
    
    def link_google(self, user_id):
        """Link Google account to existing user account."""
        data, error = get_json_or_error(request)
        if error:
            return error
        
        error = validate_required_fields(data, ["google_token"])
        if error:
            return error
        
        try:
            success, message = self.auth_service.link_google_account(user_id, data["google_token"])
            
            if success:
                return build_success_response(
                    "Google account linked successfully.",
                    "Liên kết tài khoản Google thành công.",
                    "00093",
                    {"message": message}
                )
            else:
                return build_error_response(
                    message,
                    "Liên kết tài khoản Google thất bại.",
                    "00094"
                )
        except Exception as e:
            return build_error_response(
                "An error occurred while linking Google account.",
                "Đã xảy ra lỗi khi liên kết tài khoản Google.",
                "00095"
            )
    
    def refresh_token(self):
        data, error = get_json_or_error(request)
        if error:
            return error
        
        error = validate_required_fields(data, ["refresh_token"])
        if error:
            return error
        
        user_id = self.auth_service.verify_refresh_token(data["refresh_token"])
        
        if user_id is None:
            return build_error_response(
                "Invalid token. Token may have expired.",
                "Token không hợp lệ. Token có thể đã hết hạn.",
                "00012"
            )
            
        new_access_token = self.auth_service.generate_access_token(user_id)

        return build_success_response(
            "Token refreshed successfully.",
            "Token đã được làm mới thành công.",
            "00065",
            {"access_token": new_access_token}
        )
    
    def logout(self, user_id):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return build_error_response(
                "Invalid token.",
                "Token không hợp lệ. Token có thể đã hết hạn.",
                "00012",
                401
            )
            
        access_token = auth_header.split(" ")[1]
        
        if self.auth_service.invalidate_token(user_id, access_token):
            return "", 204
        
        return build_error_response(
            "Invalid token.",
            "Token không hợp lệ. Token có thể đã hết hạn.",
            "00012",
            401
        )
    
    def register(self):
        @rate_limit(
            max_requests=Config.RATE_LIMIT_REGISTER,
            window_seconds=Config.RATE_LIMIT_REGISTER_WINDOW,
            identifier_func=get_identifier_by_email,
            key_prefix='register'
        )
        def _register_handler():
            data, error = get_json_or_error(request)
            if error:
                return error
            
            REQUIRED_FIELDS = {"email", "password", "username", "name", "language", "timezone", "deviceId"}
            error = validate_required_fields(data, REQUIRED_FIELDS)
            if error:
                return error
            
            error = validate_email(data["email"])
            if error:
                return error
            
            existed_user = self.auth_service.check_email_registered(data["email"])
            if existed_user:
                return build_error_response(
                    "An account with this email address already exists.",
                    "Một tài khoản với địa chỉ email này đã tồn tại.",
                    "00032"
                )
                
            if not self.auth_service.validate_password(data["password"]):
                return build_error_response(
                    "Your password should be between 6 and 20 characters long.",
                    "Vui lòng cung cấp một mật khẩu dài hơn 6 và ngắn hơn 20 ký tự.",
                    "00066"
                )
                
            if self.auth_service.is_duplicated_username(data["username"]):
                return build_error_response(
                    "This username is already in use.",
                    "Username này đã được sử dụng.",
                    "00067"
                )
                
            new_user = self.auth_service.save_new_user(
                data["email"], data["password"], data["username"], 
                data["name"], data["language"], data["timezone"], data["deviceId"]
            )
            
            # Generate verification code để verify email
            verification_code = self.auth_service.generate_verification_code(new_user.email)
            confirm_token = self.auth_service.generate_confirm_token(new_user.email)
            
            try:
                send_email(
                    to=new_user.email,
                    subject="Verify Your Email Address for Travel Agent P",
                    template="verify-email",
                    user=new_user,
                    code=verification_code
                )
            except Exception as e:
                logging.error(f"Error sending verification email: {str(e)}")
                # Vẫn trả về thành công nhưng báo lỗi gửi email
                return build_error_response(
                    "Registration successful but failed to send verification email. Please try resending the verification code.",
                    "Đăng ký thành công nhưng không thể gửi email xác minh. Vui lòng thử gửi lại mã xác minh.",
                    "EMAIL_SEND_FAILED",
                    201
                )
            
            # KHÔNG trả về access_token và refresh_token
            # User phải verify email trước khi login
            return build_success_response(
                "Registration successful. Please check your email to verify your account before logging in.",
                "Đăng ký thành công. Vui lòng kiểm tra email để xác minh tài khoản trước khi đăng nhập.",
                "00035",
                {
                    "user": new_user.as_dict(exclude=["password_hash"]),
                    "confirmToken": confirm_token,
                    "message": "Please verify your email before logging in"
                },
                201
            )
        
        return _register_handler()
    
    def send_verification_code(self):
        data, error = get_json_or_error(request)
        if error:
            return error
        
        error = validate_required_fields(data, ["email"])
        if error:
            return error
            
        error = validate_email(data["email"])
        if error:
            return error

        registered_user = self.auth_service.check_email_registered(data["email"])
        if not registered_user:
            return build_error_response(
                "Your email has not been activated, please register first.",
                "Email không liên kết với tài khoản nào, vui lòng đăng ký trước.",
                "00043"
            )
            
        if self.auth_service.is_verified(data["email"]):
            return build_error_response(
                "Your email has already been verified.",
                "Email của bạn đã được xác minh.",
                "00046"
            )
        
        return build_success_response(
            "Registration successful.",
            "Đã đăng ký thành công.",
            "00053"
        )
    
    def verify_email(self):
        data, error = get_json_or_error(request)
        if error:
            return error
        
        error = validate_required_fields(data, ["confirm_token", "verification_code"])
        if error:
            return error
        
        user = self.auth_service.verify_verification_code(data["confirm_token"], data["verification_code"])
        if user and self.auth_service.verify_user_email(user.email):
            # Chỉ xác nhận verification thành công
            # KHÔNG trả về tokens - user phải login
            return build_success_response(
                "Your email address has been verified successfully. Please login to continue.",
                "Địa chỉ email của bạn đã được xác minh thành công. Vui lòng đăng nhập để tiếp tục.",
                "00058",
                {
                    "verified": True,
                    "email": user.email
                }
            )
        else:
            return build_error_response(
                "The code you entered does not match the code we sent to your email. Please check again.",
                "Mã bạn nhập không khớp với mã chúng tôi đã gửi đến email của bạn. Vui lòng kiểm tra lại.",
                "00054"
            )
    
    def request_reset_password(self):
        @rate_limit(
            max_requests=Config.RATE_LIMIT_RESET_PASSWORD,
            window_seconds=Config.RATE_LIMIT_RESET_PASSWORD_WINDOW,
            identifier_func=get_identifier_by_email,
            key_prefix='reset_password'
        )
        def _request_reset_handler():
            data, error = get_json_or_error(request)
            if error:
                return error
            
            error = validate_required_fields(data, ["email"])
            if error:
                return error
                
            error = validate_email(data["email"])
            if error:
                return error

            registered_user = self.auth_service.check_email_registered(data["email"])
            if not registered_user:
                return build_error_response(
                    "Your email has not been registered, please register first.",
                    "Email của bạn chưa được đăng ký, vui lòng đăng ký trước.",
                    "00043"
                )
                
            reset_code = self.auth_service.generate_reset_code(data["email"])
            reset_token = self.auth_service.generate_reset_token(data["email"])
            send_email(
                to=data["email"], 
                subject="Reset Your Password from Travel Agent P",
                template="reset-password",
                user=registered_user,
                code=reset_code
            )

            return build_success_response(
                "Reset code has been sent to your email successfully.",
                "Mã reset đã được gửi đến email của bạn thành công.",
                "00048",
                {"resetToken": reset_token}
            )
        
        return _request_reset_handler()
    
    def validate_reset_code(self):
        data, error = get_json_or_error(request)
        if error:
            return error
        
        error = validate_required_fields(data, ["resetToken", "resetCode"])
        if error:
            return error

        user = self.auth_service.verify_reset_code(data["resetToken"], data["resetCode"])
        if user:
            temp_access_token = self.auth_service.generate_access_token(user.id)
            return build_success_response(
                "Reset code is valid.",
                "Mã reset hợp lệ.",
                "00048",
                {"tempAccessToken": temp_access_token}
            )
        else:
            return build_error_response(
                "The code you entered does not match the code we sent to your email. Please check again.",
                "Mã bạn nhập không khớp với mã chúng tôi đã gửi đến email của bạn. Vui lòng kiểm tra lại.",
                "00054"
            )
    
    def reset_password(self):
        data, error = get_json_or_error(request)
        if error:
            return error
        
        error = validate_required_fields(data, ["tempAccessToken", "newPassword"])
        if error:
            return error

        user_id = self.auth_service.verify_temp_access_token(data["tempAccessToken"])
        if not user_id:
            return build_error_response(
                "Invalid token. Token may have expired.",
                "Token không hợp lệ. Token có thể đã hết hạn.",
                "00012"
            )
            
        if self.auth_service.set_password(user_id, data["newPassword"]):
            return build_success_response(
                "Your password has been reset successfully.",
                "Mật khẩu của bạn đã được đặt lại thành công.",
                "00058"
            )
        
        return build_error_response(
            "Invalid token.",
            "Token không hợp lệ.",
            "00012"
        )


# Create the controller instance
def init_auth_controller():
    container = DIContainer.get_instance()
    auth_service = container.resolve(AuthService.__name__)
    return AuthController(auth_service)
