from app import celery, create_app
from config import Config

app = create_app()
app.app_context().push()

celery.conf.update(
    worker_pool=Config.CELERY_WORKER_POOL,
)