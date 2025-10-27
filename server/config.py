import os
from dotenv import load_dotenv
from pathlib import Path


env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "secret_key")
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL")

    POSTGRES_USERNAME = os.environ.get("POSTGRES_USER")
    POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
    POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
    POSTGRES_DBNAME = os.environ.get("POSTGRES_DB_NAME")

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        if POSTGRES_USERNAME and POSTGRES_HOST and POSTGRES_DBNAME:
            SQLALCHEMY_DATABASE_URI = (
                f"postgresql+psycopg2://{POSTGRES_USERNAME}:{POSTGRES_PASSWORD or ''}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DBNAME}"
            )
        else:
            pass
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")
    MAIL_SUBJECT_PREFIX = "[Travel Agent P]"
    
    FIREBASE_CREDENTIALS_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH")
    FIREBASE_STORAGE_BUCKET = os.environ.get("FIREBASE_STORAGE_BUCKET")

    ACCESS_TOKEN_EXPIRE_SEC = int(os.environ.get("ACCESS_TOKEN_EXPIRE_SEC", 3600))
    REFRESH_TOKEN_EXPIRE_SEC = int(os.environ.get("REFRESH_TOKEN_EXPIRE_SEC", 604800))
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    # Redis Configuration
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
    REDIS_DB = int(os.environ.get("REDIS_DB", 0))
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)
    
    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "True").lower() == "true"
    RATE_LIMIT_LOGIN = int(os.environ.get("RATE_LIMIT_LOGIN", 5))  # 5 attempts
    RATE_LIMIT_LOGIN_WINDOW = int(os.environ.get("RATE_LIMIT_LOGIN_WINDOW", 300))  # 5 minutes
    RATE_LIMIT_REGISTER = int(os.environ.get("RATE_LIMIT_REGISTER", 3))  # 3 attempts
    RATE_LIMIT_REGISTER_WINDOW = int(os.environ.get("RATE_LIMIT_REGISTER_WINDOW", 3600))  # 1 hour
    RATE_LIMIT_RESET_PASSWORD = int(os.environ.get("RATE_LIMIT_RESET_PASSWORD", 3))
    RATE_LIMIT_RESET_PASSWORD_WINDOW = int(os.environ.get("RATE_LIMIT_RESET_PASSWORD_WINDOW", 3600))
    
    # Cache Configuration
    CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "True").lower() == "true"
    CACHE_DEFAULT_TTL = int(os.environ.get("CACHE_DEFAULT_TTL", 300))  # 5 minutes
    CACHE_USER_PROFILE_TTL = int(os.environ.get("CACHE_USER_PROFILE_TTL", 600))  # 10 minutes


secret_key = Config.SECRET_KEY
access_token_expire_sec = Config.ACCESS_TOKEN_EXPIRE_SEC
refresh_token_expire_sec = Config.REFRESH_TOKEN_EXPIRE_SEC
google_client_id = Config.GOOGLE_CLIENT_ID
google_client_secret = Config.GOOGLE_CLIENT_SECRET