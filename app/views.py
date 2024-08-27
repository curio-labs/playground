from celery.result import AsyncResult
import datetime
import random
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

REPLICATION_PERIODS = [
    (datetime.time(0, 0), datetime.time(0, 30)),
    (datetime.time(6, 0), datetime.time(6, 30)),
    (datetime.time(12, 0), datetime.time(12, 30)),
    (datetime.time(18, 0), datetime.time(18, 30)),
]

READABLE_PERIODS = [
    ("00:00", "00:30"),
    ("06:00", "06:30"),
    ("12:00", "12:30"),
    ("18:00", "18:30"),
]


def index(request):
    return render(request, "index.html")


def simple_ranking(request):
    return render(request, "simple_ranking.html")


def score_ranking(request):
    attributes = services.get_attributes()
    return render(request, "score_ranking.html", {"attributes": attributes})


def get_repeat_stories(story_ids):
    stories = services.get_stories_by_id(story_ids=story_ids)
    stories = [
        md.Story(
            id=story["id"],
            title=story["title"],
            text=story["text"],
            published_at=story["published_at"],
            publication=story["publication"],
            author=story["author"],
            type=story["type"],
            classification=story["classification"],
        )
        for story in stories["data"]
    ]
    return stories


def get_random_stories(batch_size=1000, limit=20):
    stories = services.get_stories(limit=batch_size)["data"]
    random.shuffle(stories)
    stories = stories[:limit]
    return [
        md.Story(
            id=story["id"],
            title=story["title"],
            text=story["text"],
            published_at=story["published_at"],
            publication=story["publication"],
            author=story["author"],
            type=story["type"],
            classification=story["classification"],
        )
        for story in stories
    ]


@csrf.csrf_exempt
@http.require_POST
def simple_ranking_prompt(request):
    now = datetime.datetime.now().time()
    for start_time, end_time in REPLICATION_PERIODS:
        if start_time <= now <= end_time:
            html = f"""
                <p>The database is currently replicating. Please try again later.</p>
                <p>Replication occurs daily during the following periods:</p>
                <ul>
                    <li>00:00-00:30</li>
                    <li>06:00-06:30</li>
                    <li>12:00-12:30</li>
                    <li>18:00-18:30</li>
                </ul>
            """
            return HttpResponse(html)
    prompt_value = request.POST.get("prompt-value")
    batch_size = int(request.POST.get("batch-size"))
    story_limit = int(request.POST.get("story-limit"))
    if story_limit > batch_size:
        html = f"""
            <p>Story limit cannot exceed batch size.</p>
            <p>Please try again.</p>
        """
        return HttpResponse(html)
    stories = get_random_stories(batch_size=batch_size, limit=story_limit)
    data = services.make_llm_request_for_story_batch(
        stories=stories,
        prompt=prompt_value,
        limit=story_limit,
    )
    html = render_to_string("stories_list.html", {"stories": data})
    return HttpResponse(html)


@csrf.csrf_exempt
@http.require_POST
def score_ranking_prompt(request):
    now = datetime.datetime.now().time()
    for start_time, end_time in REPLICATION_PERIODS:
        if start_time <= now <= end_time:
            html = f"""
                <p>The database is currently replicating. Please try again later.</p>
                <p>Replication occurs daily during the following periods:</p>
                <ul>
                    <li>00:00-00:30</li>
                    <li>06:00-06:30</li>
                    <li>12:00-12:30</li>
                    <li>18:00-18:30</li>
                </ul>
            """
            return HttpResponse(html)
    story_ids = request.POST.getlist("story-id")
    prompt_value = request.POST.get("prompt-value")
    selected_attributes = []
    for key in request.POST:
        if key.startswith("attribute-"):
            selected_attributes.append(request.POST[key])
    if not story_ids:
        batch_size = int(request.POST.get("batch-size"))
        story_limit = int(request.POST.get("story-limit"))
        if story_limit > batch_size:
            html = f"""
                <p>Story limit cannot exceed batch size.</p>
                <p>Please try again.</p>
            """
            return HttpResponse(html)
        stories = get_random_stories(batch_size=batch_size, limit=story_limit)
    else:
        stories = get_repeat_stories(story_ids=story_ids)

    data = services.make_concurrent_llm_requests_for_stories(
        stories=stories,
        prompt=prompt_value,
        attributes=selected_attributes,
    )
    html = render_to_string("score_stories_list.html", {"stories": data})
    return HttpResponse(html)


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
        story = services.get_stories_by_id([story_id])["data"][0]

        # Render the story into the story_detail.html template
        story_html = render_to_string("story_detail.html", {"story": story})

        # Return the rendered HTML as part of a JSON response
        return HttpResponse(story_html)

    except Exception as e:
        raise Http404(f"Story with ID {story_id} not found: {e}")


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

    except httpx.RequestError:
        return HttpResponse("Error fetching external paragraphs.", status=500)
    except Exception as e:
        raise Http404(f"Story with ID {story_id} not found: {e}")


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
