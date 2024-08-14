from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone

from .models import Task

logger = get_task_logger(__name__)


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
