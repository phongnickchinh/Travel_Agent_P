import pymysql
import logging

from flask import Flask
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
from celery import Celery
from flask_apscheduler import APScheduler
from bson import ObjectId
from datetime import datetime



from config import Config
from .common.errors import handle_exception


# Custom JSON Provider to handle MongoDB ObjectId and datetime (Flask 3.x)
class MongoJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)





class Base(DeclarativeBase):
    pass
db = SQLAlchemy(model_class=Base)
migrate = Migrate()
mail = Mail()
celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)
scheduler = APScheduler()



def create_app(config_class=Config):
    # NEED FIX: logout endpoint is not working, access token not being add to blacklist property. Big issue. Do not delete this message unless you fixed it..
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Setup logging (console + file)
    from .common.logging_config import setup_logging
    setup_logging(app)
    
    # Set custom JSON provider to handle MongoDB ObjectId (Flask 3.x)
    app.json = MongoJSONProvider(app)
    
    CORS(app, resources={r"/*": {
        "origins": ["https://phamphong.id.vn", "http://localhost:5173", "http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": "*",
        "expose_headers": "*",
        "supports_credentials": False
    }})
    
    # Initialize Redis connection
    from .core.clients.redis_client import RedisClient
    init_logger = logging.getLogger(__name__)
    try:
        RedisClient.get_instance()
        init_logger.info("[INIT] Redis initialized successfully")
    except Exception as e:
        init_logger.warning(f"[INIT] Redis initialization failed: {str(e)}")
        init_logger.warning("[INIT] Application will continue in degraded mode (without Redis features)")
    
    # Initialize MongoDB connection and create indexes
    from .core.clients.mongodb_client import get_mongodb_client
    try:
        mongodb_client = get_mongodb_client()
        if mongodb_client.is_healthy():
            init_logger.info("[INIT] MongoDB initialized successfully")
            # Create indexes on first startup
            mongodb_client.create_indexes()
            init_logger.info("[INIT] MongoDB indexes created/verified")
        else:
            init_logger.warning("[INIT] MongoDB connection not healthy")
    except Exception as e:
        init_logger.warning(f"[INIT] MongoDB initialization failed: {str(e)}")
        init_logger.warning("[INIT] POI and Itinerary features will not be available")
    
    # Initialize Elasticsearch and sync data from MongoDB
    from .core.es_initializer import initialize_elasticsearch
    try:
        es_success = initialize_elasticsearch()
        if es_success:
            init_logger.info("[INIT] Elasticsearch initialized and synced successfully")
        else:
            init_logger.warning("[INIT] Elasticsearch initialization incomplete")
    except Exception as es_error:
        init_logger.warning(f"[INIT] Elasticsearch initialization failed: {str(es_error)}")
    
    from .utils.blacklist_cleaner import cleanup_expired_tokens
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    
    # Configure Celery with proper timeout and connection settings for long-running tasks (e.g., LLM generation)
    # NOTE: These settings (socket_timeout, socket_connect_timeout) are for Celery result backend communication
    # They are INDEPENDENT from Redis cache TTL (CACHE_DEFAULT_TTL) and do NOT affect cache expiration
    
    # Broker transport options for TLS (rediss://) support
    broker_transport_opts = {
        'retry_on_timeout': True,
        'socket_connect_timeout': Config.CELERY_SOCKET_CONNECT_TIMEOUT,
        'socket_timeout': Config.CELERY_SOCKET_TIMEOUT,
        'max_retries': Config.CELERY_SOCKET_MAX_RETRIES,
    }
    
    # Result backend transport options (same as broker for consistency)
    result_backend_transport_opts = {
        'retry_on_timeout': True,
        'socket_connect_timeout': Config.CELERY_SOCKET_CONNECT_TIMEOUT,
        'socket_timeout': Config.CELERY_SOCKET_TIMEOUT,
        'max_retries': Config.CELERY_SOCKET_MAX_RETRIES,
    }
    
    # Add SSL cert requirements for rediss:// URLs (both broker and result backend)
    if Config.CELERY_BROKER_URL and Config.CELERY_BROKER_URL.startswith('rediss://'):
        import ssl
        broker_transport_opts['ssl_cert_reqs'] = ssl.CERT_NONE  # Accept self-signed certs
        result_backend_transport_opts['ssl_cert_reqs'] = ssl.CERT_NONE
    
    celery.conf.update(
        app.config,
        # Task result configuration
        result_expires=Config.CELERY_RESULT_EXPIRES,
        task_track_started=True,
        task_acks_late=True,  # Task ack after execution, not before
        # Broker transport options (for TLS support)
        broker_transport_options=broker_transport_opts,
        # Redis result backend connection settings (handle long-running tasks like LLM generation)
        result_backend_transport_options=result_backend_transport_opts,
        # Broker connection resilience
        broker_pool_limit=0,  # Unlimited connection pool
        broker_connection_retry=True,
        broker_connection_retry_on_startup=True,
        broker_connection_max_retries=None,  # Infinite retries
        # Worker settings
        worker_prefetch_multiplier=Config.CELERY_PREFETCH_MULTIPLIER,
        worker_max_tasks_per_child=Config.CELERY_MAX_TASKS_PER_CHILD,
    )
    
    # Auto migrate upgrade on server restart
    with app.app_context():
        try:
            from flask_migrate import upgrade
            init_logger.info("Running database migration...")
            upgrade()
            init_logger.info("Database migration completed successfully")
        except Exception as e:
            init_logger.error(f"Database migration failed: {str(e)}")
            init_logger.warning("Server will continue startup - please check migrations manually if needed")
            # Continue startup even if migration fails
    
    from .model.base_model import BaseModel
    
    # Import and initialize DI after models are imported
    from .core.di import init_di
    init_di()
    
    from .controller.auth import init_app as auth_api_init
    auth_api = auth_api_init()
    app.register_blueprint(auth_api)
    
    # Register Admin authentication blueprint
    from .controller.admin import init_app as admin_api_init
    admin_api = admin_api_init()
    app.register_blueprint(admin_api)

    from .controller.user import init_app as user_api_init
    user_api = user_api_init()
    app.register_blueprint(user_api)
    
    # Register POI/Places blueprints
    from .controller.places import init_app as places_api_init
    places_api = places_api_init()
    app.register_blueprint(places_api)
    
    from .controller.search import init_app as search_api_init
    search_api = search_api_init()
    app.register_blueprint(search_api)
    
    # Register Autocomplete v2 blueprint (Hybrid ES + Google)
    from .controller.autocomplete import init_app as autocomplete_api_init
    autocomplete_api = autocomplete_api_init()
    app.register_blueprint(autocomplete_api)
    
    # Register Plan blueprint (Week 4)
    from .controller.plan import init_app as plan_api_init
    plan_api = plan_api_init()
    app.register_blueprint(plan_api)

    # # Register health check endpoint
    from .controller.health import init_app as health_api_init
    health_api = health_api_init()
    app.register_blueprint(health_api)

    app.register_error_handler(Exception, handle_exception)

    return app