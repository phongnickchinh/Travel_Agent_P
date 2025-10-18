from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from .baseModel import BaseModel
from app import Base 

if TYPE_CHECKING:
    from .user import User

class Role(BaseModel):
    __tablename__ = 'roles'
    
    role_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    users = relationship(
        "User", 
        secondary="user_roles",
        back_populates="roles",
        lazy="select" 
    )

    def __init__(self, role_name: str, **kwargs):
        self.role_name = role_name

    def __repr__(self):
        return f"<Role id='{self.id}' name='{self.role_name}'>"


class UserRole(Base): # Association table, not from BaseModel
    __tablename__ = 'user_roles' # Table name
    
    # Composite PK
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True) # FK to users.id
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True) # FK to roles.id

    # No common BaseModel fields (id, created_at, etc.) needed here.

    # Optional: direct relationships from UserRole instance
    # user = relationship("User")
    # role = relationship("Role")

    def __init__(self, user_id: str, role_id: str):
        self.user_id = user_id
        self.role_id = role_id

    def as_dict(self):
        """Dict representation of UserRole."""
        return {
            'user_id': self.user_id,
            'role_id': self.role_id
        }

    def __repr__(self):
        return f"<UserRole user_id='{self.user_id}' role_id='{self.role_id}'>"

# Reminder: In User model (app/models/user.py), define the reverse relationship:
# class User(UserMixin, BaseModel):
#     # ...
#     roles = relationship(
#         "Role",
#         secondary="user_roles",
#         back_populates="users",
#         lazy="select"
#     )
#     # ...
