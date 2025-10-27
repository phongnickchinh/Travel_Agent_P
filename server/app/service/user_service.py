import logging
from ..repo.postgre.interfaces.user_repository_interface import UserInterface
from ..core.di_container import DIContainer


class UserService:
    def __init__(self, user_repo: UserInterface):
        """
        Initialize UserService with injected dependencies.
        
        Args:
            user_repo: User repository implementation
        """
        self.user_repository = user_repo

    def delete_user_account(self, user):
        try:
            self.user_repository.delete_user(user)
        except Exception as e:
            logging.error(f"Error deleting account user: {str(e)}")
            raise