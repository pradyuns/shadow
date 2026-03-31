from celery import Celery

from app.logging_config import setup_logging

setup_logging()

celery_app = Celery("competitor_monitor")

celery_app.config_from_object("workers.celery_config")
celery_app.conf.update(
    include=[
        "workers.tasks.scraping",
        "workers.tasks.diffing",
        "workers.tasks.analysis",
        "workers.tasks.notifications",
        "workers.tasks.maintenance",
        "workers.tasks.email_verification",
    ]
)
