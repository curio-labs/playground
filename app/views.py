import datetime
import logging
import httpx
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators import csrf, http

from app import repo
from src import constants, firebase, services
from src.services.headlines import HeadlineStoryQueryStrategy

logger = logging.getLogger(__name__)


def index(request):
    return render(request, "index.html")


def score_ranking(request):
    attributes = constants.STORY_ATTRIBUTES_UI
    return render(request, "score_ranking.html", {"attributes": attributes})


def news_ranking(request):
    return render(
        request,
        "news_ranking.html",
    )


@csrf.csrf_exempt
@http.require_POST
def rerank_stories(request):
    story_ids = request.POST.getlist("story-id")
    vector_positions = request.POST.getlist("vector-position")
    similarity_scores = request.POST.getlist("similarity-score")
    prompt_value = request.POST.get("prompt-value")
    selected_attributes = [
        request.POST[key] for key in request.POST if key.startswith("attribute-")
    ]
    for start_time, end_time in constants.REPLICATION_PERIODS:
        now = datetime.datetime.now().time()
        if start_time <= now <= end_time:
            return HttpResponse(constants.REPLICATING_HTML_MSG)

    stories = []
    for story_id, vector_position, similarity_score in zip(
        story_ids, vector_positions, similarity_scores
    ):
        stories.append(
            {
                "id": story_id,
                "vector_position": int(vector_position),
                "similarity_score": float(similarity_score),
            }
        )

    stories = repo.stories.get_repeat_stories(stories=stories)
    stories = sorted(stories, key=lambda x: x.position, reverse=False)
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
@http.require_POST
def score_ranking_prompt(request):
    prompt_value = request.POST.get("prompt-value")
    story_limit = int(request.POST.get("story-limit"))
    is_vector_search = request.POST.get("is-vector-search")
    vector_query = request.POST.get("vector-query")
    sampling_method = request.POST.get("sampling-method")
    logger.info(f"Score Ranking|Vector Query: {vector_query}|Prompt: {prompt_value}")
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

    try:
        stories = repo.stories.get_random_stories(
            query=prompt_value,
            is_vector_search=is_vector_search,
            vector_search=vector_query,
            start_date=start_date,
        )
    except ValueError as e:
        html = f"""
            <p>{e}</p>
            <p>Please try again.</p>
        """
        return HttpResponse(html)
    llm_stories = services.sampling.sample_stories(
        stories=stories,
        limit=story_limit,
        sampling_method=sampling_method,
    )
    data = services.make_concurrent_llm_requests_for_stories(
        stories=llm_stories,
        prompt=prompt_value,
        attributes=selected_attributes,
    )
    html = render_to_string(
        "score_stories_list.html", {"llm_stories": data, "vector_stories": stories}
    )
    return HttpResponse(html)


@csrf.csrf_exempt
@http.require_POST
def news_ranking_prompt(request):
    prompt_value = request.POST.get("prompt-value")
    news_market = request.POST.get("news-market")
    selected_news_feed = request.POST.get("selected-news-feed")
    is_top_headlines = selected_news_feed == "top-headlines"
    headline_limit = int(request.POST.get("headline-limit"))
    story_matching_strategy = request.POST.get("internal-story-matching")
    logger.info(f"News Ranking|Market: {news_market}|Prompt: {prompt_value}")

    try:
        headlines = services.headlines.get_all_bing_news_headlines(
            market=news_market,
            use_top_headlines_feed=is_top_headlines,
            headline_limit=headline_limit,
        )
    except ValueError as e:
        html = f"""
            <p>{e}</p>
            <p>Please try again.</p>
        """
        return HttpResponse(html)

    reranked_headlines = services.llm.make_concurrent_llm_request_for_headline_scoring(
        headlines=headlines, relevancy_prompt=prompt_value
    )

    if story_matching_strategy is None:
        scored_story_matches = None
    else:
        story_matching_strategy = HeadlineStoryQueryStrategy.from_user_str(
            story_matching_strategy
        )
        scored_story_matches = services.headlines.match_headlines_to_internal_stories(
            [headline for headline, _ in reranked_headlines], story_matching_strategy
        )

    if scored_story_matches is not None:
        context = {
            "headlines": headlines,
            "reranked_headlines_and_stories": list(
                zip(reranked_headlines, scored_story_matches)
            ),
            "has_story_matches": True,
        }
    else:
        context = {
            "headlines": headlines,
            "reranked_headlines": reranked_headlines,
            "has_story_matches": False,
        }
    html = render_to_string(
        "reranked_headlines_table.html",
        context,
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
