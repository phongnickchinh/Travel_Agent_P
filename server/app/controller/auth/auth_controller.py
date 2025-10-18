from flask import request, jsonify
from validate_email_address import validate_email

from . import auth_api
from ...service.auth_service import AuthService
from ...email import send_email
from ...utils.middleware import JWT_required
from ...core.di_container import DIContainer


class AuthController:
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
        self._register_routes()
    
    def _register_routes(self):
        """Register all routes with Flask."""
        auth_api.add_url_rule("/login", "login", self.login, methods=["POST"])
        auth_api.add_url_rule("/refresh-token", "refresh_token", self.refresh_token, methods=["POST"])
        auth_api.add_url_rule("/logout", "logout", self._wrap_jwt_required(self.logout), methods=["POST"])
        auth_api.add_url_rule("/register", "register", self.register, methods=["POST"])
        auth_api.add_url_rule("/send-verification-code", "send_verification_code", 
                             self.send_verification_code, methods=["POST"])
        auth_api.add_url_rule("/verify-email", "verify_email", self.verify_email, methods=["POST"])
        auth_api.add_url_rule("/request-reset-password", "request_reset_password", 
                             self.request_reset_password, methods=["POST"])
        auth_api.add_url_rule("/validate-reset-code", "validate_reset_code", 
                             self.validate_reset_code, methods=["POST"])
        auth_api.add_url_rule("/reset-password", "reset_password", self.reset_password, methods=["POST"])
    
    def _wrap_jwt_required(self, f):
        """Helper to maintain JWT required middleware while using class methods."""
        @JWT_required
        def wrapper(user_id):
            return f(user_id)
        return wrapper
    
    def login(self):
        data = request.get_json()
        if data is None:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid JSON data.",
                    "vn": "Dữ liệu JSON không hợp lệ."
                },
                "resultCode": "00004"
            }), 400
        
        email = data.get("email")
        password = data.get("password")
        
        if email is None or password is None:
            return jsonify({
                "resultMessage": {
                    "en": "Please provide all required fields!",
                    "vn": "Vui lòng cung cấp tất cả các trường bắt buộc!"
                },
                "resultCode": "00025"
            }), 400
            
        if not validate_email(email):
            return jsonify({
                "resultMessage": {
                    "en": "Please provide a valid email address!",
                    "vn": "Vui lòng cung cấp một địa chỉ email hợp lệ!"
                },
                "resultCode": "00026"
            }), 400

        user, role = self.auth_service.validate_login(email, password)
        if not user:
            return jsonify({
                "resultMessage": {
                    "en": "You have entered an invalid email or password.",
                    "vn": "Bạn đã nhập một email hoặc mật khẩu không hợp lệ."
                },
                "resultCode": "00045"
            }), 400
            
        access_token = self.auth_service.generate_access_token(user.id)
        refresh_token = self.auth_service.generate_refresh_token(user.id)

        return jsonify({
            "resultMessage": {
                "en": "You have successfully logged in.",
                "vn": "Bạn đã đăng nhập thành công."
            },
            "resultCode": "00047",
            "user": user.as_dict(exclude=["password_hash"]),
            "role": role,
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 200
    
    def refresh_token(self):
        data = request.get_json()
        if data is None:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid JSON data.",
                    "vn": "Dữ liệu JSON không hợp lệ."
                },
                "resultCode": "00004"
            }), 400
        
        refresh_token = data.get("refresh_token")
        
        if refresh_token is None:
            return jsonify({
                "resultMessage": {
                    "en": "Please provide all required fields!",
                    "vn": "Vui lòng cung cấp tất cả các trường bắt buộc!"
                },
                "resultCode": "00025"
            }), 400
        
        user_id = self.auth_service.verify_refresh_token(refresh_token)
        
        if user_id is None:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid token. Token may have expired.",
                    "vn": "Token không hợp lệ. Token có thể đã hết hạn."
                },
                "resultCode": "00012"
            }), 400
            
        new_access_token = self.auth_service.generate_access_token(user_id)
        # new_refresh_token = self.auth_service.generate_refresh_token(user_id)

        return jsonify({
            "resultMessage": {
                "en": "Token refreshed successfully.",
                "vn": "Token đã được làm mới thành công."
            },
            "resultCode": "00065",
            "access_token": new_access_token,
            # "refresh_token": new_refresh_token
        }), 200
    
    def logout(self, user_id):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({
                "resultMessage": {
                    "en": "Invalid token.",
                    "vn": "Token không hợp lệ. Token có thể đã hết hạn."
                },
                "resultCode": "00012"
            }), 401
            
        # Extract the token from the Authorization header
        access_token = auth_header.split(" ")[1]
        
        if self.auth_service.invalidate_token(user_id, access_token):
            return "", 204
        
        return jsonify({
            "resultMessage": {
                "en": "Invalid token.",
                "vn": "Token không hợp lệ. Token có thể đã hết hạn."
            },
            "resultCode": "00012"
        }), 401
    
    def register(self):
        data = request.get_json()
        if data is None:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid JSON data.",
                    "vn": "Dữ liệu JSON không hợp lệ."
                },
                "resultCode": "00004"
            }), 400
        
        REQUIRED_FIELDS = {"email", "password", "username", "name", "language", "timezone", "deviceId"}
        missing_fields = {field for field in REQUIRED_FIELDS if data.get(field) is None}
        
        if missing_fields:
            return jsonify({
                "resultMessage": {
                    "en": "Please provide all required fields!",
                    "vn": "Vui lòng cung cấp tất cả các trường bắt buộc!"
                },
                "resultCode": "00025"
            }), 400
        
        if not validate_email(data["email"]):
            return jsonify({
                "resultMessage": {
                    "en": "Please provide a valid email address!",
                    "vn": "Vui lòng cung cấp một địa chỉ email hợp lệ!"
                },
                "resultCode": "00026"
            }), 400
        
        existed_user = self.auth_service.check_email_registered(data["email"])
        if existed_user:
            return jsonify({
                "resultMessage": {
                    "en": "An account with this email address already exists.",
                    "vn": "Một tài khoản với địa chỉ email này đã tồn tại."
                },
                "resultCode": "00032"
            }), 400
            
        if not self.auth_service.validate_password(data["password"]):
            return jsonify({
                "resultMessage": {
                    "en": "Your password should be between 6 and 20 characters long.",
                    "vn": "Vui lòng cung cấp một mật khẩu dài hơn 6 và ngắn hơn 20 ký tự."
                },
                "resultCode": "00066"
            }), 400
            
        if self.auth_service.is_duplicated_username(data["username"]):
            return jsonify({
                "resultMessage": {
                    "en": "This username is already in use.",
                    "vn": "Username này đã được sử dụng."
                },
                "resultCode": "00067"
            }), 400
            
        new_user = self.auth_service.save_new_user(
            data["email"], data["password"], data["username"], 
            data["name"], data["language"], data["timezone"], data["deviceId"]
        )
        verification_code = self.auth_service.generate_verification_code(new_user.email)
        confirm_token = self.auth_service.generate_confirm_token(new_user.email)
        # send_email(
        #     to=data["email"], 
        #     subject="Your Verification Code from Meal Planner",
        #     template="confirm",
        #     user=new_user,
        #     code=verification_code
        # )
        
        return jsonify({
            "resultMessage": {
                "en": "You registered successfully.",
                "vn": "Bạn đã đăng ký thành công."
            },
            "resultCode": "00035",
            "user": new_user.as_dict(exclude=["password_hash"]),
            "verificationCode": verification_code,
            "role": "user",
            "confirmToken": confirm_token
        }), 201
    
    def send_verification_code(self):
        data = request.get_json()
        if data is None:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid JSON data.",
                    "vn": "Dữ liệu JSON không hợp lệ."
                },
                "resultCode": "00004"
            }), 400
        
        email = data.get("email")

        if not email:
            return jsonify({
                "resultMessage": {
                    "en": "Please provide all required fields!",
                    "vn": "Vui lòng cung cấp tất cả các trường bắt buộc!"
                },
                "resultCode": "00025"
            }), 400
            
        if not validate_email(email):
            return jsonify({
                "resultMessage": {
                    "en": "Please provide a valid email address!",
                    "vn": "Vui lòng cung cấp một địa chỉ email hợp lệ!"
                },
                "resultCode": "00026"
            }), 400

        registered_user = self.auth_service.check_email_registered(email)
        if not registered_user:
            return jsonify({
                "resultMessage": {
                    "en": "Your email has not been activated, please register first.",
                    "vn": "Email của bạn chưa được kích hoạt, vui lòng đăng ký trước."
                },
                "resultCode": "00043"
            }), 400
            
        if self.auth_service.is_verified(email):
            return jsonify({
                "resultMessage": {
                    "en": "Your email has already been verified.",
                    "vn": "Email của bạn đã được xác minh."
                },
                "resultCode": "00046"
            }), 400

        verification_code = self.auth_service.generate_verification_code(email)
        confirm_token = self.auth_service.generate_confirm_token(email)
        send_email(
            to=data["email"], 
            subject="Your Verification Code from Meal Planner",
            template="confirm",
            user=registered_user,
            code=verification_code
        )

        return jsonify({
            "resultMessage": {
                "en": "Code has been sent to your email successfully.",
                "vn": "Mã đã được gửi đến email của bạn thành công."
            },
            "resultCode": "00048",
            "confirmToken": confirm_token
        }), 200
    
    def verify_email(self):
        data = request.get_json()
        if data is None:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid JSON data.",
                    "vn": "Dữ liệu JSON không hợp lệ."
                },
                "resultCode": "00004"
            }), 400
        
        confirm_token = data.get("confirm_token")
        verification_code = data.get("verification_code")

        if not confirm_token or not verification_code:
            return jsonify({
                "resultMessage": {
                    "en": "Please provide all required fields!",
                    "vn": "Vui lòng cung cấp tất cả các trường bắt buộc!"
                },
                "resultCode": "00025"
            }), 400
        
        user = self.auth_service.verify_verification_code(confirm_token, verification_code)
        if user and self.auth_service.verify_user_email(user.email):
            access_token = self.auth_service.generate_access_token(user.id)
            refresh_token = self.auth_service.generate_refresh_token(user.id)
            return jsonify({
                "resultMessage": {
                    "en": "Your email address has been verified successfully.",
                    "vn": "Địa chỉ email của bạn đã được xác minh thành công."
                },
                "resultCode": "00058",
                "access_token": access_token,
                "refresh_token": refresh_token
            }), 200
        else:
            return jsonify({
                "resultMessage": {
                    "en": "The code you entered does not match the code we sent to your email. Please check again.",
                    "vn": "Mã bạn nhập không khớp với mã chúng tôi đã gửi đến email của bạn. Vui lòng kiểm tra lại."
                },
                "resultCode": "00054"
            }), 400
    
    def request_reset_password(self):
        data = request.get_json()
        if data is None:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid JSON data.",
                    "vn": "Dữ liệu JSON không hợp lệ."
                },
                "resultCode": "00004"
            }), 400
        
        email = data.get("email")
        if not email:
            return jsonify({
                "resultMessage": {
                    "en": "Please provide all required fields!",
                    "vn": "Vui lòng cung cấp tất cả các trường bắt buộc!"
                },
                "resultCode": "00025"
            }), 400
            
        if not validate_email(email):
            return jsonify({
                "resultMessage": {
                    "en": "Please provide a valid email address!",
                    "vn": "Vui lòng cung cấp một địa chỉ email hợp lệ!"
                },
                "resultCode": "00026"
            }), 400

        registered_user = self.auth_service.check_email_registered(email)
        if not registered_user:
            return jsonify({
                "resultMessage": {
                    "en": "Your email has not been registered, please register first.",
                    "vn": "Email của bạn chưa được đăng ký, vui lòng đăng ký trước."
                },
                "resultCode": "00043"
            }), 400
            
        reset_code = self.auth_service.generate_reset_code(email)
        reset_token = self.auth_service.generate_reset_token(email)
        send_email(
            to=email, 
            subject="Reset Your Password from Meal Planner",
            template="reset-password",
            user=registered_user,
            code=reset_code
        )

        return jsonify({
            "resultMessage": {
                "en": "Reset code has been sent to your email successfully.",
                "vn": "Mã reset đã được gửi đến email của bạn thành công."
            },
            "resultCode": "00048",
            "resetToken": reset_token
        }), 200
    
    def validate_reset_code(self):
        data = request.get_json()
        if not data:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid JSON data.",
                    "vn": "Dữ liệu JSON không hợp lệ."
                },
                "resultCode": "00004"
            }), 400
        
        reset_token = data.get("resetToken")
        reset_code = data.get("resetCode")
        if not reset_token or not reset_code:
            return jsonify({
                "resultMessage": {
                    "en": "Please provide all required fields!",
                    "vn": "Vui lòng cung cấp tất cả các trường bắt buộc!"
                },
                "resultCode": "00025"
            }), 400

        user = self.auth_service.verify_reset_code(reset_token, reset_code)
        if user:
            temp_access_token = self.auth_service.generate_access_token(user.id)
            return jsonify({
                "resultMessage": {
                    "en": "Reset code is valid.",
                    "vn": "Mã reset hợp lệ."
                },
                "resultCode": "00048",
                "tempAccessToken": temp_access_token
            }), 200
        else:
            return jsonify({
                "resultMessage": {
                    "en": "The code you entered does not match the code we sent to your email. Please check again.",
                    "vn": "Mã bạn nhập không khớp với mã chúng tôi đã gửi đến email của bạn. Vui lòng kiểm tra lại."
                },
                "resultCode": "00054"
            }), 400
    
    def reset_password(self):
        data = request.get_json()
        if not data:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid JSON data.",
                    "vn": "Dữ liệu JSON không hợp lệ."
                },
                "resultCode": "00004"
            }), 400
        
        temp_access_token = data.get("tempAccessToken")
        new_password = data.get("newPassword")
        if not temp_access_token or not new_password:
            return jsonify({
                "resultMessage": {
                    "en": "Please provide all required fields!",
                    "vn": "Vui lòng cung cấp tất cả các trường bắt buộc!"
                },
                "resultCode": "00025"
            }), 400

        user_id = self.auth_service.verify_temp_access_token(temp_access_token)
        if not user_id:
            return jsonify({
                "resultMessage": {
                    "en": "Invalid token. Token may have expired.",
                    "vn": "Token không hợp lệ. Token có thể đã hết hạn."
                },
                "resultCode": "00012"
            }), 400
            
        if self.auth_service.set_password(user_id, new_password):
            return jsonify({
                "resultMessage": {
                    "en": "Your password has been reset successfully.",
                    "vn": "Mật khẩu của bạn đã được đặt lại thành công."
                },
                "resultCode": "00058"
            }), 200
        
        return jsonify({
            "resultMessage": {
                "en": "Invalid token.",
                "vn": "Token không hơp lệ."
            },
            "resultCode": "00012"
        }), 400


# Create the controller instance
def init_auth_controller():
    container = DIContainer.get_instance()
    auth_service = container.resolve(AuthService.__name__)
    return AuthController(auth_service)
