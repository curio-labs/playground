import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("playground")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"

app.conf.beat_schedule = {
    "fetch-stories-every-10-seconds": {
        "task": "app.tasks.fetch_stories",
        "schedule": 10.0,
    },
}
