from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from ..core.base_model import BaseModel 

class Token(BaseModel):
    __tablename__ = 'tokens'
    
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    refresh_token: Mapped[Optional[str]] = mapped_column(String(512), unique=True, nullable=True, index=True)
    confirm_token: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True) 
    reset_token: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    
    verification_code: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    verification_code_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    reset_code: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    reset_code_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship('User', back_populates='tokens', foreign_keys=[user_id])

    def __init__(self, 
                 user_id: str, 
                 refresh_token: Optional[str] = None, 
                 confirm_token: Optional[str] = None,
                 reset_token: Optional[str] = None,
                 verification_code: Optional[str] = None, 
                 verification_code_expires_at: Optional[datetime] = None,
                 **kwargs):
        
        self.user_id = user_id
        self.refresh_token = refresh_token
        self.confirm_token = confirm_token
        self.reset_token = reset_token
        self.verification_code = verification_code
        self.verification_code_expires_at = verification_code_expires_at

    def set_refresh_token(self, token: str):
        self.refresh_token = token

    def set_verification_code(self, code: str, expires_at: datetime):
        self.verification_code = code
        self.verification_code_expires_at = expires_at

    def set_reset_token(self, token: str, expires_at: Optional[datetime] = None):
        self.reset_token = token
        # if expires_at:
            # self.reset_token_expires_at = expires_at # This field was commented out in the previous version, re-evaluate if needed

    def __repr__(self):
        return f"<Token id='{self.id}' user_id='{self.user_id}'>"


