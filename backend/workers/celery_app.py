from celery import Celery

from app.config import settings
from app.logging_config import setup_logging

setup_logging()

celery_app = Celery("competitor_monitor")

celery_app.config_from_object("workers.celery_config")
celery_app.autodiscover_tasks(["workers.tasks"])
