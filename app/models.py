from django.db import models
import uuid


class Task(models.Model):
    TASK_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("STARTED", "Started"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    task_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=20, choices=TASK_STATUS_CHOICES, default="PENDING"
    )
    result = models.TextField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_completed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Task {self.task_id} - {self.status}"

    class Meta:
        db_table = "tasks"


class Story(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    text = models.TextField()
    published_at = models.DateTimeField()
    publication = models.TextField(null=True)
    author = models.CharField(max_length=1024, null=True)
    type = models.CharField(max_length=1024, null=True)
    classification = models.CharField(max_length=1024, null=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "stories"
