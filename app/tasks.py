from celery import shared_task
from celery.utils.log import get_task_logger

from app import models as md
from src import services

logger = get_task_logger(__name__)


@shared_task
def fetch_stories():
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
