import pymysql

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
from .errors import handle_exception


# Custom JSON Provider to handle MongoDB ObjectId and datetime (Flask 3.x)
class MongoJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# Removing the import that causes circular imports
# from .AppConfig.di_setup import init_di


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
    from .logging_config import setup_logging
    setup_logging(app)
    
    # Set custom JSON provider to handle MongoDB ObjectId (Flask 3.x)
    app.json = MongoJSONProvider(app)
    
    CORS(app, resources={r"/*": {
        "origins": "*", 
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": "*",
        "expose_headers": "*"
    }})
    
    # Initialize Redis connection
    from .core.redis_client import RedisClient
    try:
        RedisClient.get_instance()
        print("[INIT] Redis initialized successfully")
    except Exception as e:
        print(f"[INIT] WARNING: Redis initialization failed: {str(e)}")
        print("[INIT] WARNING: Application will continue in degraded mode (without Redis features)")
    
    # Initialize MongoDB connection and create indexes
    from .core.mongodb_client import get_mongodb_client
    try:
        mongodb_client = get_mongodb_client()
        if mongodb_client.is_healthy():
            print("[INIT] MongoDB initialized successfully")
            # Create indexes on first startup
            mongodb_client.create_indexes()
            print("[INIT] MongoDB indexes created/verified")
        else:
            print("[INIT] WARNING: MongoDB connection not healthy")
    except Exception as e:
        print(f"[INIT] WARNING: MongoDB initialization failed: {str(e)}")
        print("[INIT] WARNING: POI and Itinerary features will not be available")
    
    from .utils.blacklist_cleaner import cleanup_expired_tokens
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    celery.conf.update(app.config)
    
    # Auto migrate upgrade on server restart
    with app.app_context():
        try:
            from flask_migrate import upgrade
            print("Running database migration...")
            upgrade()
            print("Database migration completed successfully")
        except Exception as e:
            print(f"Database migration failed: {str(e)}")
            print("Server will continue startup - please check migrations manually if needed")
            # Continue startup even if migration fails
    
    from .core.base_model import BaseModel
    
    # Import and initialize DI after models are imported
    from .config.di_setup import init_di
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

    # # Register health check endpoint
    from .controller.health import init_app as health_api_init
    health_api = health_api_init()
    app.register_blueprint(health_api)

    app.register_error_handler(Exception, handle_exception)

    return app