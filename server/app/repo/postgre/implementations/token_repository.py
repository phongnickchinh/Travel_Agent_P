from datetime import datetime, timezone, timedelta
import logging

from ..interfaces.token_repository_interface import TokenInterface
from ....model.token import Token as TokenModel
from ....model.blacklist import Blacklist as BlacklistModel
from .... import db

class TokenRepository(TokenInterface):
    def __init__(self):
        pass
    
    
    def get_token_by_user_id(self, user_id):
        return db.session.execute(
            db.select(TokenModel).where(TokenModel.user_id == user_id)
        ).scalar()
    
    
    def _upsert_token(self, user_id, commit=True, **fields):
        """
        Private helper to fetch-or-create token row and update fields.
        
        Args:
            user_id: User ID
            commit: Nếu True, commit ngay vào DB. Nếu False, chỉ add/update trong session.
            **fields: Field names and values to set
            
        Raises:
            Exception: If database operation fails
        """
        try:
            token = db.session.execute(
                db.select(TokenModel).where(TokenModel.user_id == user_id)
            ).scalar()
            
            if not token:
                token = TokenModel(user_id=user_id, **fields)
                db.session.add(token)
            else:
                for field_name, field_value in fields.items():
                    setattr(token, field_name, field_value)
            
            if commit:
                db.session.commit()
            else:
                db.session.flush()  # Flush để có thể query trong cùng transaction
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error upserting token: {str(e)}")
            raise
        
        
    def save_new_refresh_token(self, user_id, new_refresh_token, commit=True):
        self._upsert_token(user_id, commit=commit, refresh_token=new_refresh_token)
    
    def save_verification_code(self, user_id, code, commit=True):
        self._upsert_token(
            user_id,
            commit=commit,
            verification_code=code,
            verification_code_expires_at=datetime.now(tz=timezone.utc) + timedelta(minutes=10)
        )
        
    def save_reset_code(self, user_id, code, commit=True):
        self._upsert_token(
            user_id,
            commit=commit,
            reset_code=code,
            reset_code_expires_at=datetime.now(tz=timezone.utc) + timedelta(minutes=10)
        )
        
    def save_confirm_token(self, user_id, token, commit=True):
        self._upsert_token(user_id, commit=commit, confirm_token=token)
        
    def save_reset_token(self, user_id, token, commit=True):
        self._upsert_token(user_id, commit=commit, reset_token=token)
        
        
    def delete_refresh_token(self, user_id):
        try:
            token = self.get_token_by_user_id(user_id)
            if not token:
                return False
            
            token.refresh_token = None
            db.session.commit()
            return True
        
        except Exception as e:
            db.session.rollback() 
            logging.error(f"Error deleting refresh token: {str(e)}")
            raise