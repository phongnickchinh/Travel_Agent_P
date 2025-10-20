from typing import Optional
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import expression
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


from .baseModel import BaseModel

class User(BaseModel):
    __tablename__ = 'users'
    
    # Các trường id, created_at, updated_at, is_deleted đã được kế thừa từ BaseModel

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Nullable for OAuth users
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default='en', server_default='en')
    # timezone không có trong __init__ gốc, nên để nullable=True
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    deviceId: Mapped[str] = mapped_column(String(255), nullable=False) # Giữ nguyên, vì có trong __init__
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Tăng độ dài cho URL
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default=expression.false())
    
    # OAuth fields
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    auth_provider: Mapped[str] = mapped_column(String(20), default='local', server_default='local', nullable=False)  # 'local', 'google', or 'both'
    profile_picture: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Google profile picture URL

    roles = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="select"
    )
    tokens = relationship('Token', back_populates='user', cascade="all, delete-orphan", lazy='dynamic')
    blacklist = relationship('Blacklist', back_populates='user', cascade="all, delete-orphan", lazy='dynamic')

    def __init__(self, email: str, username: str, name: str, deviceId: str,
                password: Optional[str] = None, language: str = 'en', timezone: Optional[str] = None,
                avatar_url: Optional[str] = None, is_verified: bool = False, 
                google_id: Optional[str] = None, auth_provider: str = 'local',
                profile_picture: Optional[str] = None, **kwargs):
        """
        Hàm khởi tạo cho User.
        Các trường id, created_at, updated_at, is_deleted sẽ được SQLAlchemy/BaseModel xử lý qua default.
        """
        self.email = email
        if password:  # Only set password for local auth
            self.set_password(password)
        self.username = username
        self.name = name
        self.deviceId = deviceId
        self.language = language
        self.timezone = timezone
        self.avatar_url = avatar_url
        self.google_id = google_id
        self.auth_provider = auth_provider
        self.profile_picture = profile_picture
        self.is_verified = is_verified


    def set_password(self, password: str):
        """Hash và đặt mật khẩu."""
        self.password_hash = generate_password_hash(password)


    def check_password(self, password: str) -> bool:
        """Kiểm tra mật khẩu đã hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def has_local_auth(self) -> bool:
        """Check if user can login with password."""
        return self.password_hash is not None and self.auth_provider in ['local', 'both']
    
    def has_google_auth(self) -> bool:
        """Check if user can login with Google."""
        return self.google_id is not None and self.auth_provider in ['google', 'both']


    def to_display_dict(self):
        """
        Trả về một dictionary đại diện cho thông tin user thường dùng để hiển thị,
        loại trừ các trường nhạy cảm và bao gồm các property từ UserMixin.
        """
        # Sử dụng as_dict từ BaseModel và loại trừ password_hash
        data = super().as_dict(exclude=['password_hash'])
        return data
    

    def __repr__(self):
        return f"<User username='{self.username}' email='{self.email}'>"

