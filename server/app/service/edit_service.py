import logging

from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from ..core.di_container import DIContainer

from ..repo.interfaces.user_repository_interface import UserInterface
from ..utils.firebase_interface import FirebaseInterface


class EditService:
    def __init__(self, user_repo: UserInterface, firebase_helper: FirebaseInterface):
        """
        Initialize EditService with injected dependencies.
        
        Args:
            user_repo: User repository implementation
            firebase_helper: Firebase service implementation
        """
        self.user_repository = user_repo
        self.firebase_helper = firebase_helper

    def verify_old_password(self, user, old_password):
        if not check_password_hash(user.password_hash, old_password):
            return False
            
        return True

    
    def save_new_password(self, user, new_password):
        try:
            self.user_repository.update_password(user, new_password)
        except Exception as e:
            logging.error(f"Error saving new password: {str(e)}")
            raise
        
        
    def update_user_info(self, user, data, image_file):
        try:
            if data:
                self.user_repository.update_user(user, data)
                
            if image_file:
                filename = secure_filename(image_file.filename)
                image_url = self.firebase_helper.upload_image(image_file, f"user_avatars/{filename}")
                self.user_repository.update_user(user, {"avatar_url": image_url})
                
            return user

        except Exception as e:
            logging.error(f"Error updating user info: {str(e)}")
            raise