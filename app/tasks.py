from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone

from app import models as md
from src import services

logger = get_task_logger(__name__)


@shared_task
def fetch_stories():
    print("Fetching stories...")
    stories = services.get_stories(limit=1000)

    for story in stories["data"]:
        if md.Story.objects.filter(id=story["id"]).exists():
            continue
        md.Story.objects.create(
            id=story["id"],
            title=story["title"],
            text=story["text"],
            published_at=story["published_at"],
            publication=story["publication"],
            author=story["author"],
            type=story["type"],
            classification=story["classification"],
        )


@shared_task(bind=True)
def add(self, x, y):
    import time

    # Simulate a long-running task
    time.sleep(10)

    result = x + y

    # Update the Task record in the database
    try:
        task_entry = Task.objects.get(task_id=self.request.id)
        task_entry.status = "SUCCESS"
        task_entry.result = result
        task_entry.date_completed = timezone.now()
        task_entry.save()
        logger.info(f"Task {self.request.id} completed successfully.")
    except Task.DoesNotExist:
        logger.error(f"Task {self.request.id} not found in database.")

    return result
