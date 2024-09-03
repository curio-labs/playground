import datetime
import httpx
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators import csrf, http

from app import repo
from src import services, firebase, constants


def index(request):
    return render(request, "index.html")


def score_ranking(request):
    attributes = constants.STORY_ATTRIBUTES_UI
    return render(request, "score_ranking.html", {"attributes": attributes})


@csrf.csrf_exempt
@http.require_POST
def score_ranking_prompt(request):
    story_ids = request.POST.getlist("story-id")
    prompt_value = request.POST.get("prompt-value")
    story_limit = int(request.POST.get("story-limit"))
    is_vector_search = request.POST.get("is-vector-search")
    vector_search = request.POST.get("vector-search")
    start_date = (
        datetime.datetime.now()
        - datetime.timedelta(days=int(request.POST.get("start-date")))
    ).isoformat()
    selected_attributes = [
        request.POST[key] for key in request.POST if key.startswith("attribute-")
    ]

    for start_time, end_time in constants.REPLICATION_PERIODS:
        now = datetime.datetime.now().time()
        if start_time <= now <= end_time:
            return HttpResponse(constants.REPLICATING_HTML_MSG)

    if not story_ids:
        try:
            stories = repo.stories.get_random_stories(
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
        stories = repo.stories.get_repeat_stories(story_ids=story_ids)

    data = services.make_concurrent_llm_requests_for_stories(
        stories=stories,
        prompt=prompt_value,
        attributes=selected_attributes,
    )
    html = render_to_string(
        "score_stories_list.html", {"llm_stories": data, "vector_stories": stories}
    )
    return HttpResponse(html)


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
        token = firebase.get_firebase_token()
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
