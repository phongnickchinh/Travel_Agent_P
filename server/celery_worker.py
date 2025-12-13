from app import celery, create_app
from config import Config

app = create_app()
app.app_context().push()

# Configure Celery worker pool based on OS
celery.conf.update(
    worker_pool=Config.CELERY_WORKER_POOL,
)