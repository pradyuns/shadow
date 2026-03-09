from celery import Celery

from app.config import settings

celery_app = Celery("competitor_monitor")

celery_app.config_from_object("workers.celery_config")
celery_app.autodiscover_tasks(["workers.tasks"])
