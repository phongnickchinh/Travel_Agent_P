import os
from dotenv import load_dotenv
from pathlib import Path


env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "secret_key")
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL")
    
    # Celery Worker Pool: Windows uses 'solo' (no multiprocessing),
    # Linux/Mac use 'prefork' for better performance
    CELERY_WORKER_POOL = os.environ.get("CELERY_WORKER_POOL")
    if not CELERY_WORKER_POOL:
        CELERY_WORKER_POOL = "solo" if os.name == "nt" else "prefork"
    
    # Celery Result Backend & Worker Timeout Settings
    # NOTE: These are INDEPENDENT from cache TTL and do NOT affect Redis cache expiration
    # They only control how long Celery waits for task results from Redis
    CELERY_RESULT_EXPIRES = int(os.environ.get("CELERY_RESULT_EXPIRES", 3600))  # 1 hour
    CELERY_SOCKET_CONNECT_TIMEOUT = int(os.environ.get("CELERY_SOCKET_CONNECT_TIMEOUT", 10))  # 10 seconds
    CELERY_SOCKET_TIMEOUT = int(os.environ.get("CELERY_SOCKET_TIMEOUT", 30))  # 30 seconds (for long tasks)
    CELERY_SOCKET_MAX_RETRIES = int(os.environ.get("CELERY_SOCKET_MAX_RETRIES", 5))
    CELERY_PREFETCH_MULTIPLIER = int(os.environ.get("CELERY_PREFETCH_MULTIPLIER", 1))
    CELERY_MAX_TASKS_PER_CHILD = int(os.environ.get("CELERY_MAX_TASKS_PER_CHILD", 100))

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
    # Plan creation rate limit (default: 5 plans per hour)
    RATE_LIMIT_PLAN_CREATION = int(os.environ.get("RATE_LIMIT_PLAN_CREATION", 5))
    RATE_LIMIT_PLAN_CREATION_WINDOW = int(os.environ.get("RATE_LIMIT_PLAN_CREATION_WINDOW", 3600))
    # Generic rate limit key prefix
    RATE_LIMIT_KEY_PREFIX = os.environ.get("RATE_LIMIT_KEY_PREFIX", "travel_agent:rate_limit")
    
    # Cache Configuration
    CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "True").lower() == "true"
    CACHE_DEFAULT_TTL = int(os.environ.get("CACHE_DEFAULT_TTL", 300))  # 5 minutes
    CACHE_USER_PROFILE_TTL = int(os.environ.get("CACHE_USER_PROFILE_TTL", 600))  # 10 minutes
    
    # Elasticsearch Configuration
    ELASTICSEARCH_ENABLED = os.environ.get("ELASTICSEARCH_ENABLED", "True").lower() == "true"
    ELASTICSEARCH_POI_INDEX = os.environ.get("ELASTICSEARCH_POI_INDEX", "pois")
    ELASTICSEARCH_CONFIG_FILE_PATH = os.environ.get("ELASTICSEARCH_CONFIG_FILE_PATH", "repo/es/mappings/poi_index_mapping.json")
    ELASTICSEARCH_TIMEOUT = int(os.environ.get("ELASTICSEARCH_TIMEOUT", 30))
    ELASTICSEARCH_MAX_RETRIES = int(os.environ.get("ELASTICSEARCH_MAX_RETRIES", 3))
    
    # HuggingFace + LangChain Configuration (Week 4)
    HUGGINGFACE_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")
    HUGGINGFACE_MODEL = os.environ.get("HUGGINGFACE_MODEL", "meta-llama/Llama-3.2-3B-Instruct")
    LANGCHAIN_MAX_RETRIES = int(os.environ.get("LANGCHAIN_MAX_RETRIES", 3))
    LANGCHAIN_TIMEOUT = int(os.environ.get("LANGCHAIN_TIMEOUT", 120))
    
    # Groq API Configuration (FREE for development)
    # Get free API key at: https://console.groq.com
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile")
    
    # LLM Provider Selection: "groq" (free/fast), "huggingface", "openai"
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq")
    
    # Mock POI Configuration
    MOCK_POI_ENABLED = os.environ.get("MOCK_POI_ENABLED", "True").lower() == "true"


secret_key = Config.SECRET_KEY
access_token_expire_sec = Config.ACCESS_TOKEN_EXPIRE_SEC
refresh_token_expire_sec = Config.REFRESH_TOKEN_EXPIRE_SEC
google_client_id = Config.GOOGLE_CLIENT_ID
google_client_secret = Config.GOOGLE_CLIENT_SECRET