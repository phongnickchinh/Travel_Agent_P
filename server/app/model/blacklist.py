
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from .base_model import BaseModel


class Blacklist(BaseModel):
    __tablename__ = "blacklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(255), nullable=False)

    user = relationship('User', back_populates='blacklist', foreign_keys=[user_id])

    def __init__(self, user_id: str, token: str):
        self.user_id = user_id
        self.token = token
    def __repr__(self):
        return f"<Blacklist id='{self.id}' user_id='{self.user_id}' token='{self.token}'>"
