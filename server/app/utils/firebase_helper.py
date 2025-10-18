from flask import current_app as app
import firebase_admin
from firebase_admin import credentials, storage
from .firebase_interface import FirebaseInterface
import time
import uuid


class FirebaseHelper(FirebaseInterface):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseHelper, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _initialize(self):
        """Initialize Firebase only when needed"""
        if not self._initialized:
            try:
                if not firebase_admin._apps:
                    cred = credentials.Certificate(app.config["FIREBASE_CREDENTIALS_PATH"])
                    firebase_admin.initialize_app(cred, {
                        'storageBucket': app.config["FIREBASE_STORAGE_BUCKET"]
                    })
                self.bucket = storage.bucket()
                self._initialized = True
            except Exception as e:
                print(f"Firebase initialization error: {str(e)}")
                raise

    def upload_image(self, file, filename):
        """Upload image to Firebase Storage
        Args:
            file: File object to upload
            filename: Path in storage (e.g. 'groups/avatar1.jpg')
        Returns:
            str: Public URL of uploaded file or None if failed
        """
        self._initialize()
        try:
            # Thêm timestamp và unique ID để tránh cache issues
            timestamp = int(time.time())
            unique_id = str(uuid.uuid4())[:8]
            
            # Tách tên file và extension
            if '.' in filename:
                name, ext = filename.rsplit('.', 1)
                unique_filename = f"{name}_{timestamp}_{unique_id}.{ext}"
            else:
                unique_filename = f"{filename}_{timestamp}_{unique_id}"
            
            blob = self.bucket.blob(unique_filename)
            blob.upload_from_file(file, content_type=file.content_type)
            blob.make_public()
            return blob.public_url
        except Exception as e:
            print(f"Upload error: {str(e)}")
            return None

    def delete_image(self, image_url):
        """Delete image from Firebase Storage by URL
        Args:
            image_url: Public URL of the image to delete
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        self._initialize()
        try:
            # Extract blob name from URL
            # URL format: https://storage.googleapis.com/bucket-name/path/to/file
            bucket_name = app.config["FIREBASE_STORAGE_BUCKET"]
            base_url = f"https://storage.googleapis.com/{bucket_name}/"
            
            if image_url.startswith(base_url):
                blob_name = image_url[len(base_url):]
                blob = self.bucket.blob(blob_name)
                blob.delete()
                return True
            else:
                print(f"Invalid image URL format: {image_url}")
                return False
        except Exception as e:
            print(f"Delete error: {str(e)}")
            return False
