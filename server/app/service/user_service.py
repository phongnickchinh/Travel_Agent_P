import logging
from ..repo.user_interface import UserInterface
from ..core.di_container import DIContainer


class UserService:
    def __init__(self):
        container = DIContainer.get_instance()
        self.user_repository = container.resolve(UserInterface.__name__)

    def delete_user_account(self, user):
        try:
            self.user_repository.delete_user(user)
        except Exception as e:
            logging.error(f"Error deleting account user: {str(e)}")
            raise