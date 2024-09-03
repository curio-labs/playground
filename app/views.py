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


def get_random_stories(
    limit=20,
    is_vector_search=False,
    vector_search=None,
    query=None,
    start_date=None,
):
    if is_vector_search:
        if query is None or start_date is None:
            raise ValueError(
                "Query and Start Date must be provided when vector_search is True."
            )
        vector_stories = services.get_vector_search_stories(
            start_date=start_date,
            limit=1_000,
            vector_search=vector_search,
        )
        story_ids = [story["id"] for story in vector_stories]
        stories = services.get_stories_by_id(story_ids=story_ids)["data"]
        for story in stories:
            story["similarity_score"] = next(
                item["similarity_score"]
                for item in vector_stories
                if item["id"] == story["id"]
            )
        random.shuffle(stories)
        stories = sorted(
            stories[:limit], key=lambda x: x["similarity_score"], reverse=True
        )

    else:
        stories = services.get_stories(limit=1_000, start_date=start_date)["data"]
        random.shuffle(stories)
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
            similarity_score=round(story.get("similarity_score", 0), 2),
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
    story_limit = int(request.POST.get("story-limit"))
    stories = get_random_stories(limit=story_limit)
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
                    <li>01:00-01:30</li>
                    <li>07:00-07:30</li>
                    <li>13:00-13:30</li>
                    <li>19:00-19:30</li>
                </ul>
            """
            return HttpResponse(html)
    story_ids = request.POST.getlist("story-id")
    prompt_value = request.POST.get("prompt-value")
    if not story_ids:
        story_limit = int(request.POST.get("story-limit"))
        is_vector_search = request.POST.get("is-vector-search")
        vector_search = request.POST.get("vector-search")
        start_date = int(request.POST.get("start-date"))
        today = datetime.datetime.now()
        start_date = (today - datetime.timedelta(days=start_date)).isoformat()
        try:
            stories = get_random_stories(
                query=prompt_value,
                limit=story_limit,
                is_vector_search=is_vector_search,
                vector_search=vector_search,
                start_date=start_date,
            )
        except ValueError as e:
            html = f"""
                <p>{e}</p>
                <p>Please try again.</p>
            """
            return HttpResponse(html)
    else:
        stories = get_repeat_stories(story_ids=story_ids)

    selected_attributes = []
    for key in request.POST:
        if key.startswith("attribute-"):
            selected_attributes.append(request.POST[key])
    data = services.make_concurrent_llm_requests_for_stories(
        stories=stories,
        prompt=prompt_value,
        attributes=selected_attributes,
    )
    html = render_to_string(
        "dummy_score_stories_list.html",
        {"llm_stories": data, "vector_stories": stories},
    )
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
