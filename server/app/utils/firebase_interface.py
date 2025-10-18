from abc import ABC, abstractmethod

class FirebaseInterface(ABC):
    @abstractmethod
    def upload_image(self, file, filename):
        """Upload image to Firebase Storage
        Args:
            file: File object to upload
            filename: Path in storage (e.g. 'groups/avatar1.jpg')
        Returns:
            str: Public URL of uploaded file or None if failed
        """
        pass

    @abstractmethod
    def delete_image(self, image_url):
        """Delete image from Firebase Storage by URL
        Args:
            image_url: Public URL of the image to delete
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        pass
