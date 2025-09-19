from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "refresh-prices-every-12h": {
        "task": "product.tasks.refresh_all_prices",
        "schedule": crontab(hour="*/12"),
    },
    "bulk-parse-hobbygames-every-3-days": {
        "task": "product.tasks.bulk_parse_hobbygames", 
        "schedule": crontab(hour=2, minute=0, day_of_week=1),
    },
    "monitor-favorites-every-3h": {
        "task": "product.tasks.monitor_all_user_favorites",
        "schedule": crontab(minute=0, hour="*/3"),
},
}

CELERY_TASK_ROUTES = {
    "product.tasks.parse_playwright": {"queue": "heavy"},
    "product.tasks.parse_bs4": {"queue": "light"},
    "product.tasks.parse_api_json": {"queue": "light"},
}