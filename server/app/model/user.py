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
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default='en', server_default='en')
    # timezone không có trong __init__ gốc, nên để nullable=True
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    deviceId: Mapped[str] = mapped_column(String(255), nullable=False) # Giữ nguyên, vì có trong __init__
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Tăng độ dài cho URL
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default=expression.false())

    roles = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="select"
    )
    tokens = relationship('Token', back_populates='user', cascade="all, delete-orphan", lazy='dynamic')
    blacklist = relationship('Blacklist', back_populates='user', cascade="all, delete-orphan", lazy='dynamic')

    def __init__(self, email: str, password: str, username: str, name: str, deviceId: str,
                language: str = 'en', timezone: Optional[str] = None,
                 avatar_url: Optional[str] = None, is_verified: bool = False, **kwargs):
        """
        Hàm khởi tạo cho User.
        Các trường id, created_at, updated_at, is_deleted sẽ được SQLAlchemy/BaseModel xử lý qua default.
        """
        print("hehehehe \n\n\n\n")
        self.email = email
        self.set_password(password)
        self.username = username
        self.name = name
        self.deviceId = deviceId
        self.language = language
        self.timezone = timezone
        self.avatar_url = avatar_url
        self.is_verified = is_verified


    def set_password(self, password: str):
        """Hash và đặt mật khẩu."""
        self.password_hash = generate_password_hash(password)


    def check_password(self, password: str) -> bool:
        """Kiểm tra mật khẩu đã hash."""
        return check_password_hash(self.password_hash, password)


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

