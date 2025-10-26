import logging

from ..interfaces.role_repository_interface import RoleInterface, UserRoleInterface
from ...model.role import Role as RoleModel, UserRole as UserRoleModel
from ... import db


class RoleRepository(RoleInterface):
    def __init__(self):
        pass
    
    
    def get_role_by_role_name(self, role_name) -> RoleModel:
        return db.session.execute(
            db.select(RoleModel).where(RoleModel.role_name == role_name)
        ).scalar()

    
    def get_role_of_user(self, user_id) -> RoleModel:
        return db.session.execute(
            db.select(RoleModel)
            .join(UserRoleModel, RoleModel.id == UserRoleModel.role_id)
            .where(UserRoleModel.user_id == user_id)
        ).scalar()
    
    
    def create_role(self, role_name) -> RoleModel:
        try:
            new_role = RoleModel(role_name=role_name)
            db.session.add(new_role)
            db.session.commit()
            return new_role
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating role: {str(e)}")
            raise
        
        
class UserRoleRepository(UserRoleInterface):
    def __init__(self):
        pass


    def create_user_role(self, user_id, role_id, commit=True):
        try:
            new_user_role = UserRoleModel(user_id=user_id, role_id=role_id)
            db.session.add(new_user_role)
            if commit:
                db.session.commit()
            else:
                db.session.flush()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating user role: {str(e)}")
            raise