from datetime import datetime, timezone, timedelta
import logging
import random

from ..core.di_container import DIContainer
from ..repo.token_interface import TokenInterface
from ..repo.user_interface import UserInterface
from ..repo.role_interface import RoleInterface, UserRoleInterface
from ..utils.jwt_helpers import (
    encode_jwt_token,
    decode_jwt_token,
    generate_access_token as jwt_generate_access_token,
    generate_refresh_token_jwt,
    verify_token_and_get_user_id
)
from config import access_token_expire_sec, refresh_token_expire_sec

class AuthService:
    """Auth service with dependency injection."""

    def __init__(self):
        # Instead of creating repositories here, we'll resolve them from the container
        container = DIContainer.get_instance()
        self.token_repo = container.resolve(TokenInterface.__name__)
        self.user_repo = container.resolve(UserInterface.__name__)
        self.role_repository = container.resolve(RoleInterface.__name__)
        self.user_role_repository = container.resolve(UserRoleInterface.__name__)
        

    def validate_login(self, email, password):
        """Validate the login credentials of an user."""
        user = self.user_repo.get_user_by_email(email)
        if not user:
            return None, None
        
        # Check if user can login with password
        if not user.has_local_auth():
            logging.warning(f"User {email} cannot login with password (Google-only account)")
            return None, None
        
        # Verify password
        if not user.check_password(password):
            return None, None
        
        role = self.role_repository.get_role_of_user(user.id)
        return user, role.role_name


    def generate_access_token(self, user_id, expires_in=None):
        """Generate a new access token for the user."""
        try:
            # Use environment variable if expires_in is not provided
            if expires_in is None:
                expires_in = access_token_expire_sec
            return jwt_generate_access_token(user_id, expires_in)
        except Exception as e:
            logging.error(f"Error generating access token: {str(e)}")
            raise


    def generate_refresh_token(self, user_id, expires_in=None): 
        """Generate a new refresh token for the user."""
        try:
            # Use environment variable if expires_in is not provided
            if expires_in is None:
                expires_in = refresh_token_expire_sec
            new_refresh_token = generate_refresh_token_jwt(user_id, expires_in)
            self.token_repo.save_new_refresh_token(user_id, new_refresh_token)
            return new_refresh_token
        except Exception as e:
            logging.error(f"Error generating refresh token: {str(e)}")
            raise
        
        
    def verify_temp_access_token(self, token):
        """Verify if the provided temporary access token is valid and not expired."""
        try:
            user_id = verify_token_and_get_user_id(token)
            if not user_id:
                logging.warning("Access token verification failed.")
            return user_id
        except Exception as e:
            logging.error(f"Error verifying access token: {str(e)}")
            raise
        
        
    def verify_refresh_token(self, token):
        """Verify if the provided refresh token is valid and not expired."""
        try:
            payload = decode_jwt_token(token)
            if not payload:
                logging.warning("Invalid or expired refresh token.")
                return None
                
            user_id = payload.get("user_id")
            if not user_id:
                logging.warning("Token missing required field: user_id.")
                return None

            existing_token = self.token_repo.get_token_by_user_id(user_id)
            if not existing_token or existing_token.refresh_token != token:
                return None
            
            return user_id
        except Exception as e:
            logging.error(f"Error verifying refresh token: {str(e)}")
            raise
        
        
    def validate_password(self, password):
        if len(password) < 6 or len(password) >= 20:
            return False
            
        return True

        
    def check_email_registered(self, email):
        """Checks if an email is already registered."""
        return self.user_repo.get_user_by_email(email)
    
    
    def is_duplicated_username(self, username):
        """Checks if a username is already in use."""
        return self.user_repo.get_user_by_username(username) is not None


    def save_new_user(self, email, password, username, name, language, timezone, device_id):
        """Save a new user to the database."""
        try:
            new_user = self.user_repo.save_user_to_db(email, password, username, name, language, timezone, device_id)
            existed_role_for_user = self.role_repository.get_role_by_role_name("user")
            if not existed_role_for_user:
                new_role = self.role_repository.create_role("user")
                self.user_role_repository.create_user_role(new_user.id, new_role.id)
            else:
                self.user_role_repository.create_user_role(new_user.id, existed_role_for_user.id)
            
            return new_user
        
        except Exception as e:
            logging.error(f"Error saving new user: {str(e)}")
            raise
        

    def generate_verification_code(self, email):
        """Generate a new verification code for the user."""
        try:
            verification_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
            user = self.user_repo.get_user_by_email(email)
            self.token_repo.save_verification_code(user.id, verification_code)
            logging.error(f"VERIFICATION CODE: {verification_code}")
            return verification_code
        
        except Exception as e:
            logging.error(f"Error generating verification code: {str(e)}")
            raise
        
        
    def generate_reset_code(self, email):
        """Generates a reset password code for a user."""
        try:
            reset_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
            user = self.user_repo.get_user_by_email(email)
            self.token_repo.save_reset_code(user.id, reset_code)
            logging.error(f"RESET CODE: {reset_code}")
            return reset_code
        
        except Exception as e:
            logging.error(f"Error generating reset code: {str(e)}")
            raise


    def verify_verification_code(self, confirm_token, verification_code):
        """Verifies the confirmation token and verification code."""
        try:
            payload = decode_jwt_token(confirm_token)
            if not payload:
                logging.warning("Invalid or expired confirm token.")
                return None
                
            user_id = payload.get("user_id")
            if not user_id:
                logging.warning("Token missing required field: user_id.")
                return None

            token = self.token_repo.get_token_by_user_id(user_id)
            
            if (
                token is None or token.confirm_token != confirm_token or
                token.verification_code != verification_code or
                token.verification_code_expires_at < datetime.now(tz=timezone.utc)
            ):
                return None
            
            return self.user_repo.get_user_by_id(user_id)
        except Exception as e:
            logging.error(f"Error verifying verification code: {str(e)}")
            raise
        
        
    def verify_reset_code(self, reset_token, reset_code):
        """Verifies the reset password token and reset password code."""
        try:
            payload = decode_jwt_token(reset_token)
            if not payload:
                logging.warning("Invalid or expired reset token.")
                return None
                
            user_id = payload.get("user_id")
            if not user_id:
                logging.warning("Token missing required field: user_id.")
                return None

            token = self.token_repo.get_token_by_user_id(user_id)
            if (
                token is None or token.reset_token != reset_token or
                token.reset_code != reset_code or
                token.reset_code_expires_at < datetime.now(tz=timezone.utc)
            ):
                return None
            
            return self.user_repo.get_user_by_id(user_id)
        except Exception as e:
            logging.error(f"Error verifying reset code: {str(e)}")
            raise
        
        
    def generate_confirm_token(self, email, expires_in=1800):
        """Generates a confirmation token for the user."""
        try:
            user_id = self.user_repo.get_user_by_email(email).id
            new_confirm_token = encode_jwt_token(user_id, expires_in)
            self.token_repo.save_confirm_token(user_id, new_confirm_token)
            return new_confirm_token
        except Exception as e:
            logging.error(f"Error generating confirm token: {str(e)}")
            raise
        
        
    def generate_reset_token(self, email, expires_in=1800):
        """Generates a reset password token for the user."""
        try:
            user_id = self.user_repo.get_user_by_email(email).id
            new_reset_token = encode_jwt_token(user_id, expires_in)
            self.token_repo.save_reset_token(user_id, new_reset_token)
            return new_reset_token
        except Exception as e: 
            logging.error(f"Error generating reset token: {str(e)}")
            raise
        
        
    def is_verified(self, email):
        """Check if a user has been verified."""
        user = self.user_repo.get_user_by_email(email)
        if user and user.is_verified:
            return True
        
        return False
        
    # TODO: 
    def verify_user_email(self, email):
        """Verifies a user's email."""
        try:
            is_verified = self.user_repo.update_verification_status(email)
            if not is_verified:
                return False
            return True
        
        except Exception as e:
            logging.error(f"Error verifying user email: {str(e)}")
            raise
        
        
    def invalidate_token(self, user_id, access_token):
        """Invalidate a user's refresh token and access token."""

        try:
            oka = self.token_repo.delete_refresh_token(user_id);
            # save access token to blacklist
            if oka:
                return True
            return False
        except Exception as e:
            logging.error(f"Error invalidating token: {str(e)}")
            raise
        
        
    def set_password(self, user_id, new_password):
        """Set a new password for the user."""
        try:
            user = self.user_repo.get_user_by_id(user_id)
            if user is None:
                return False
            
            # Update password
            self.user_repo.update_password(user, new_password)
            
            # Update auth_provider if user has Google linked
            if user.google_id:
                user.update(auth_provider='both')
                logging.info(f"Updated auth_provider to 'both' for user {user_id}")
            
            return True
        
        except Exception as e: 
            logging.error(f"Error setting password: {str(e)}")
            raise
                
    # --- GOOGLE OAUTH METHODS ---
    def authenticate_google_user(self, google_token: str):
        """
        Authenticate user with Google OAuth token.
        Returns user and tokens if successful, None otherwise.
        """
        try:
            from ..utils.google_oauth_helper import verify_google_token
            
            # Verify Google token and get user info
            google_user_info = verify_google_token(google_token)
            if not google_user_info:
                logging.warning("Invalid Google token")
                return None, None, None
            
            google_id = google_user_info.get('sub')
            email = google_user_info.get('email')
            name = google_user_info.get('name')
            profile_picture = google_user_info.get('picture')
            email_verified = google_user_info.get('email_verified', False)
            
            if not email_verified:
                logging.warning(f"Google email not verified: {email}")
                return None, None, None
            
            # Check if user exists by Google ID
            user = self.user_repo.get_user_by_google_id(google_id)
            
            if user:
                # User exists, update profile if needed
                self.user_repo.update_google_profile(user, name, profile_picture)
            else:
                # Check if email already exists (local account)
                user = self.user_repo.get_user_by_email(email)
                if user:
                    # Link Google account to existing local account
                    # Determine new auth_provider
                    new_auth_provider = 'both' if user.password_hash else 'google'
                    
                    user.update(
                        google_id=google_id,
                        profile_picture=profile_picture,
                        auth_provider=new_auth_provider,
                        is_verified=True
                    )
                    logging.info(f"Linked Google to existing account: {email}, auth_provider={new_auth_provider}")
                else:
                    # Create new Google user
                    user = self.user_repo.create_google_user(
                        email=email,
                        name=name,
                        google_id=google_id,
                        profile_picture=profile_picture
                    )
                    
                    # Assign default role
                    default_role = self.role_repository.get_role_by_role_name("user")
                    if default_role:
                        self.user_role_repository.create_user_role(user.id, default_role.id)
            
            # Generate tokens
            access_token = self.generate_access_token(user.id)
            refresh_token = self.generate_refresh_token(user.id)
            
            # Get user role
            role = self.role_repository.get_role_of_user(user.id)
            
            return user, (access_token, refresh_token), role.role_name if role else "user"
        
        except Exception as e:
            logging.error(f"Error authenticating Google user: {str(e)}")
            raise
    
    def link_google_account(self, user_id: str, google_token: str):
        """
        Link Google account to existing user account.
        """
        try:
            from ..utils.google_oauth_helper import verify_google_token
            
            # Verify Google token
            google_user_info = verify_google_token(google_token)
            if not google_user_info:
                return False, "Invalid Google token"
            
            google_id = google_user_info.get('sub')
            profile_picture = google_user_info.get('picture')
            
            # Check if Google ID is already linked to another account
            existing_user = self.user_repo.get_user_by_google_id(google_id)
            if existing_user and existing_user.id != user_id:
                return False, "This Google account is already linked to another account"
            
            # Get current user
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Determine new auth_provider
            new_auth_provider = 'both' if user.password_hash else 'google'
            
            # Link Google account
            user.update(
                google_id=google_id,
                profile_picture=profile_picture,
                auth_provider=new_auth_provider
            )
            
            logging.info(f"Linked Google account for user {user_id}, auth_provider={new_auth_provider}")
            return True, "Google account linked successfully"
        
        except Exception as e:
            logging.error(f"Error linking Google account: {str(e)}")
            raise


