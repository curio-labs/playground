import httpx
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators import csrf, http

from src import firebase, services


@csrf.csrf_exempt
@http.require_GET
def get_story_by_id(request, story_id):
    try:
        # Fetch the story by ID
        story = services.get_stories_by_id([story_id])["data"][0]

        # Render the story into the story_detail.html template
        story_html = render_to_string("shared/story_detail.html", {"story": story})

        # Return the rendered HTML as part of a JSON response
        return HttpResponse(story_html)

    except Exception as e:
        raise Http404(f"Story with ID {story_id} not found: {e}") from None


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
        raise Http404(f"Story with ID {story_id} not found: {e}") from None
