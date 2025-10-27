import pymysql

from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
from celery import Celery
from flask_apscheduler import APScheduler



from config import Config
from .errors import handle_exception


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
    CORS(app, resources={r"/*": {
        "origins": "*", 
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": "*",
        "expose_headers": "*"
    }})
    
    # ✅ Initialize Redis connection
    from .core.redis_client import RedisClient
    try:
        RedisClient.get_instance()
        print("✅ Redis initialized successfully")
    except Exception as e:
        print(f"⚠️  Redis initialization failed: {str(e)}")
        print("⚠️  Application will continue in degraded mode (without Redis features)")
    
    # ✅ Initialize MongoDB connection and create indexes
    from .core.mongodb_client import get_mongodb_client
    try:
        mongodb_client = get_mongodb_client()
        if mongodb_client.is_healthy():
            print("✅ MongoDB initialized successfully")
            # Create indexes on first startup
            mongodb_client.create_indexes()
            print("✅ MongoDB indexes created/verified")
        else:
            print("⚠️  MongoDB connection not healthy")
    except Exception as e:
        print(f"⚠️  MongoDB initialization failed: {str(e)}")
        print("⚠️  POI and Itinerary features will not be available")
    
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
    app.register_blueprint(auth_api, url_prefix="/")

    from .controller.user import init_app as user_api_init
    user_api = user_api_init()
    app.register_blueprint(user_api, url_prefix="/user")

    # from .InvitationService.controller import init_app as guest_api_init
    # guest_api = guest_api_init()
    # app.register_blueprint(guest_api, url_prefix="/guest")

    # from .GuestBookService.controller import init_app as guestbook_api_init
    # guestbook_api = guestbook_api_init()
    # app.register_blueprint(guestbook_api, url_prefix="/guestbook")

    # # Register health check endpoint
    from .controller.health import init_app as health_api_init
    health_api = health_api_init()
    app.register_blueprint(health_api, url_prefix="/")

    app.register_error_handler(Exception, handle_exception)

    # ❌ REMOVED: Database blacklist cleanup cron job
    # Redis blacklist uses TTL for automatic cleanup - no cron needed
    # scheduler.init_app(app)
    # scheduler.start()
    # def job_wrapper():
    #     with app.app_context():
    #         cleanup_expired_tokens()
    # scheduler.add_job(id='cleanup_blacklist_job', func=job_wrapper, trigger='interval', minutes=5)

    return app