from celery.result import AsyncResult
import os
import httpx
from django.http import Http404
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators import csrf, http

from app import models as md, tasks
from src import services


def index(request):
    return render(request, "index.html")


def simple_ranking(request):
    return render(request, "simple_ranking.html")


def score_ranking(request):
    return render(request, "score_ranking.html")


def get_random_stories(limit=50):
    return md.Story.objects.order_by("?")[:limit]


@csrf.csrf_exempt
@http.require_POST
def simple_ranking_prompt(request):
    # This function should take an LLM prompt, send it as system prompt to chatgpt along with the content of
    # 50 stories from the database, and return the generated text.
    prompt_value = request.POST.get("prompt-value")
    story_limit = int(request.POST.get("story-limit"))

    stories = get_random_stories(limit=story_limit)
    data = services.make_llm_request_for_story_batch(
        stories, prompt=prompt_value, limit=story_limit
    )
    html = render_to_string("stories_list.html", {"stories": data})
    return HttpResponse(html)


@csrf.csrf_exempt
@http.require_POST
def score_ranking_prompt(request):
    story_ids = request.POST.getlist("story-id")
    prompt_value = request.POST.get("prompt-value")

    if not story_ids:
        stories = get_random_stories(limit=int(request.POST.get("story-limit")))
    else:
        stories = md.Story.objects.filter(id__in=story_ids).all()

    data = services.make_concurrent_llm_requests_for_stories(
        stories=stories,
        prompt=prompt_value,
    )
    html = render_to_string("score_stories_list.html", {"stories": data})
    return HttpResponse(html)


@csrf.csrf_exempt
@http.require_GET
def load_stories(request):
    stories = services.get_stories(limit=1000)
    md.Story.objects.all().delete()
    for story in stories["data"]:
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


@csrf.csrf_exempt
@http.require_GET
def get_story_by_id(request, story_id):
    try:
        # Fetch the story by ID
        story = md.Story.objects.get(id=story_id)

        # Render the story into the story_detail.html template
        story_html = render_to_string("story_detail.html", {"story": story})

        # Return the rendered HTML as part of a JSON response
        return HttpResponse(story_html)

    except md.Story.DoesNotExist:
        # If the story is not found, raise a 404
        raise Http404("Story not found")


@csrf.csrf_exempt
@http.require_GET
def get_script(request, story_id):
    try:

        url = f"https://api.services.curio.io/api/scripts/script/{story_id}/"
        token = get_firebase_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        response = httpx.get(url, headers=headers)

        external_data = response.json()

        paragraphs = render_to_string(
            "script.html", {"paragraphs": external_data["paragraphs"]}
        )
        return HttpResponse(paragraphs)

    except md.Story.DoesNotExist:
        raise Http404("Story not found")
    except httpx.RequestError:
        return HttpResponse("Error fetching external paragraphs.", status=500)


def get_firebase_token():
    url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    querystring = {"key": os.environ["FIREBASE_API_KEY"]}
    payload = {
        "email": os.environ["CURIO_AI_ADMIN_EMAIL"],
        "password": os.environ["CURIO_AI_ADMIN_PASSWORD"],
        "returnSecureToken": True,
    }
    headers = {"Content-Type": "application/json", "User-Agent": "insomnia/8.6.1"}

    response = httpx.post(url, json=payload, headers=headers, params=querystring)

    return response.json()["idToken"]
