from celery.result import AsyncResult
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators import csrf, http

from app import models as md, tasks
from src import services


def my_view(request):
    return render(request, "index.html", {"foo": "bar"})


def index(request):
    return HttpResponse("Now, you're at the playground index.")


@csrf.csrf_exempt
@http.require_POST
def prompt(request):
    # This function should take an LLM prompt, send it as system prompt to chatgpt along with the content of
    # 50 stories from the database, and return the generated text.
    prompt_value = request.POST.get("prompt-value")
    data = services.make_llm_request(prompt=prompt_value)
    html = render_to_string("stories_list.html", {"stories": data["stories"]})
    return HttpResponse(html)


@csrf.csrf_exempt
@http.require_GET
def load_stories(request):
    stories = services.get_stories(limit=50)
    for story in stories["data"]:
        md.Story.objects.create(
            id=story["id"],
            title=story["title"],
            text=story["text"],
            published_at=story["published_at"],
        )

    return JsonResponse(stories)


@csrf.csrf_exempt
@http.require_POST
def add_task(request):
    # Create the Celery task
    task = tasks.add.delay(2, 2)

    # Save the task information to the database
    task_entry = md.Task.objects.create(
        task_id=task.id,
        status=task.status,  # This should be 'PENDING' at this point
    )

    return JsonResponse({"id": task_entry.task_id, "response": "Task added."})


@csrf.csrf_exempt
@http.require_POST
def check_task_status(request, task_id):
    try:
        task_entry = md.Task.objects.get(task_id=task_id)
    except md.Task.DoesNotExist:
        return JsonResponse({"error": "Task not found"}, status=404)

    # Update the task status in the database if necessary
    async_result = AsyncResult(task_id)
    if async_result.status != task_entry.status:
        task_entry.status = async_result.status
        if async_result.status == "SUCCESS":
            task_entry.result = async_result.result
            task_entry.date_completed = timezone.now()
        elif async_result.status in ["FAILURE", "REVOKED"]:
            task_entry.result = str(async_result.result)
            task_entry.date_completed = timezone.now()
        task_entry.save()

    return JsonResponse(
        {
            "id": task_entry.task_id,
            "status": task_entry.status,
            "result": task_entry.result,
        }
    )
