import logging
from sqlalchemy import and_

from ..interfaces.user_repository_interface import UserInterface
from ....model.user import User as UserModel
from .... import db

class UserRepository(UserInterface):
    def __init__(self):
        # Constructor có thể dùng để inject dependencies nếu cần, ví dụ một logger riêng
        pass


    def get_user_by_id(self, id_str: str) -> UserModel | None: # Thêm type hint cho id
        return db.session.execute(
            db.select(UserModel).where(
                and_(
                    UserModel.id == id_str,
                    UserModel.is_deleted == False
                )
            )
        ).scalar_one_or_none() # scalar_one_or_none() an toàn hơn scalar()

    def get_user_by_email(self, email: str) -> UserModel | None:
        return db.session.execute(
            db.select(UserModel).where(
                and_(
                    UserModel.email == email,
                    UserModel.is_deleted == False
                )
            )
        ).scalar_one_or_none()
            
    def get_user_by_username(self, username: str) -> UserModel | None:
        return db.session.execute(
            db.select(UserModel).where(
                and_(
                    UserModel.username == username,
                    UserModel.is_deleted == False
                )
            )
        ).scalar_one_or_none()
            
    # --- CÁC PHƯƠNG THỨC GHI (CREATE, UPDATE, DELETE) - ĐƯỢC SỬA ĐỔI ---
    def save_user_to_db(self, email, password, username, name, language, timezone, device_id, avatar_url=None, is_verified=False, commit=True) -> UserModel:
        """
        Tạo một user mới và lưu vào DB sử dụng phương thức save() của model.
        
        Args:
            commit: Nếu True, commit ngay vào DB. Nếu False, chỉ add vào session (dùng cho transaction).
        """
        try:
            # UserModel.__init__ đã xử lý việc hash password
            new_user = UserModel(
                email=email,
                password=password, # UserModel.__init__ sẽ gọi set_password
                username=username,
                name=name,
                language=language,
                timezone=timezone,
                deviceId=device_id,
                avatar_url=avatar_url,
                is_verified=is_verified
            )
            # Gọi phương thức save() từ BaseModel với tham số commit
            # Nếu commit=False, chỉ add vào session mà không commit (cho phép rollback)
            return new_user.save(commit=commit) 
        
        except Exception as e: 
            # db.session.rollback() đã được xử lý trong new_user.save() nếu có lỗi
            logging.error(f"Error saving user to the database via repository: {str(e)}")
            # Bạn có thể muốn raise một exception tùy chỉnh của repository ở đây
            raise 

    def update_verification_status(self, email: str) -> bool:
        """
        Cập nhật trạng thái xác thực của user sử dụng phương thức update() hoặc save() của model.
        """
        try:
            user = self.get_user_by_email(email)
            if not user:
                return False
            
            # Sử dụng phương thức update() từ BaseModel
            user.update(is_verified=True) 
            # Hoặc:
            # user.is_verified = True
            # user.save() 
            return True
        
        except Exception as e:
            # db.session.rollback() đã được xử lý trong user.update() hoặc user.save()
            logging.error(f"Error updating verification status via repository: {str(e)}")
            raise

    def update_password(self, user: UserModel, new_password: str) -> UserModel | None:
        """
        Cập nhật mật khẩu của user sử dụng phương thức set_password và save() của model.
        """
        try:
            if not isinstance(user, UserModel): # Kiểm tra kiểu dữ liệu
                logging.error("Invalid user object passed to update_password")
                return None # Hoặc raise TypeError

            user.set_password(new_password) # UserModel có phương thức này để hash
            return user.save() # Lưu thay đổi (bao gồm cả updated_at nếu có)
        
        except Exception as e:
            # db.session.rollback() đã được xử lý trong user.save()
            logging.error(f"Error updating user password via repository: {str(e)}")
            raise
            
    def update_user(self, user: UserModel, data: dict) -> UserModel | None:
        """
        Cập nhật thông tin user với dữ liệu từ dict, sử dụng phương thức update() của model.
        """
        try:
            if not isinstance(user, UserModel):
                logging.error("Invalid user object passed to update_user")
                return None

            return user.update(**data) # Truyền dict vào phương thức update của model
        
        except Exception as e:
            # db.session.rollback() đã được xử lý trong user.update()
            logging.error(f"Error updating user via repository: {str(e)}")
            raise
            
    def delete_user(self, user: UserModel) -> UserModel | None: # Thực hiện soft delete
        """
        Đánh dấu user là đã xóa (soft delete) sử dụng phương thức soft_delete() của model.
        """
        try:
            if not isinstance(user, UserModel):
                logging.error("Invalid user object passed to delete_user")
                return None
                
            return user.soft_delete() # Gọi phương thức soft_delete từ BaseModel
        
        except Exception as e:
            # db.session.rollback() đã được xử lý trong user.soft_delete()
            logging.error(f"Error soft deleting user via repository: {str(e)}")
            raise
    
    # --- GOOGLE OAUTH METHODS ---
    def get_user_by_google_id(self, google_id: str) -> UserModel | None:
        """
        Get user by Google ID.
        """
        return db.session.execute(
            db.select(UserModel).where(
                and_(
                    UserModel.google_id == google_id,
                    UserModel.is_deleted == False
                )
            )
        ).scalar_one_or_none()
    
    def create_google_user(self, email: str, name: str, google_id: str, 
                          profile_picture: str = None, language: str = 'en') -> UserModel:
        """
        Create a new user from Google OAuth.
        """
        try:
            from ....utils.google_oauth_helper import generate_username_from_email, generate_device_id_for_oauth
            
            # Generate username and device ID
            username = generate_username_from_email(email)
            device_id = generate_device_id_for_oauth()
            
            # Create user without password (OAuth user)
            new_user = UserModel(
                email=email,
                password=None,  # No password for OAuth users
                username=username,
                name=name,
                language=language,
                timezone=None,
                deviceId=device_id,
                google_id=google_id,
                auth_provider='google',
                profile_picture=profile_picture,
                is_verified=True  # Google accounts are pre-verified
            )
            
            return new_user.save()
        
        except Exception as e:
            logging.error(f"Error creating Google user: {str(e)}")
            raise
    
    def update_google_profile(self, user: UserModel, name: str = None, 
                             profile_picture: str = None) -> UserModel | None:
        """
        Update user's Google profile information.
        """
        try:
            if not isinstance(user, UserModel):
                logging.error("Invalid user object passed to update_google_profile")
                return None
            
            update_data = {}
            if name:
                update_data['name'] = name
            if profile_picture:
                update_data['profile_picture'] = profile_picture
            
            if update_data:
                return user.update(**update_data)
            
            return user
        
        except Exception as e:
            logging.error(f"Error updating Google profile: {str(e)}")
            raise