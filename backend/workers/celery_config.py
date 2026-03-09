from celery.schedules import crontab

from app.config import settings

# Broker and backend
broker_url = settings.redis_url
result_backend = settings.redis_result_url

# Serialization
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

# Timezone
timezone = "UTC"
enable_utc = True

# Reliability
task_acks_late = True
worker_prefetch_multiplier = 1
result_expires = 604800  # 7 days

# Queues
task_default_queue = "default"

task_queues = {
    "default": {"exchange": "default", "routing_key": "default"},
    "scraper": {"exchange": "scraper", "routing_key": "scraper"},
    "analysis": {"exchange": "analysis", "routing_key": "analysis"},
}

task_routes = {
    "workers.tasks.scraping.*": {"queue": "scraper"},
    "workers.tasks.diffing.*": {"queue": "analysis"},
    "workers.tasks.analysis.*": {"queue": "analysis"},
    "workers.tasks.notifications.*": {"queue": "analysis"},
    "workers.tasks.maintenance.*": {"queue": "default"},
}

# Beat schedule
beat_schedule = {
    "scrape-cycle-every-6-hours": {
        "task": "workers.tasks.scraping.initiate_scrape_cycle",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "daily-digest": {
        "task": "workers.tasks.notifications.send_daily_digest",
        "schedule": crontab(minute=5, hour="*"),
    },
    "cleanup-old-snapshots-weekly": {
        "task": "workers.tasks.maintenance.cleanup_old_snapshots",
        "schedule": crontab(minute=0, hour=3, day_of_week=0),
    },
    "cleanup-deleted-monitors-weekly": {
        "task": "workers.tasks.maintenance.cleanup_deleted_monitors",
        "schedule": crontab(minute=0, hour=4, day_of_week=0),
    },
}
