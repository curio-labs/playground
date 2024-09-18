import datetime
import logging

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from app import repo
from src import constants, services

from .action import ActionView

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class RankingView(View, ActionView):
    template_name = "rank/index.html"

    def get(self, request):
        attributes = constants.STORY_ATTRIBUTES_UI
        return render(request, self.template_name, {"attributes": attributes})

    def save(self, request):
        prompt_name = request.POST.get("prompt-name")
        vector_query = request.POST.get("vector-query")
        start_date = request.POST.get("start-date")
        prompt_value = request.POST.get("prompt-value")
        sampling_method = request.POST.get("sampling-method")
        story_limit = request.POST.get("story-limit")
        attribute = request.POST.get("attribute")
        is_vector_search = request.POST.get("is-vector-search")
        is_gpt_ranking = request.POST.get("is-gpt-ranking")
        story_ids = request.POST.getlist("llm-story-id")
        similarity_scores = request.POST.getlist("llm-similarity-score")
        vector_positions = request.POST.getlist("llm-vector-position")

        if not prompt_name:
            return JsonResponse(
                {"status": "error", "error": "Prompt name is required."}, status=400
            )

        if not story_ids:
            return JsonResponse(
                {"status": "error", "error": "No stories selected."}, status=400
            )

        results = {
            "prompt_name": prompt_name,
            "vector_query": vector_query,
            "start_date": start_date,
            "prompt_value": prompt_value,
            "sampling_method": sampling_method,
            "story_limit": story_limit,
            "attribute": attribute,
            "is_vector_search": is_vector_search,
            "is_gpt_ranking": is_gpt_ranking,
            "story_ids": story_ids,
            "similarity_scores": similarity_scores,
            "vector_positions": vector_positions,
        }

        try:
            repo.prompt_results.save(results=results, playground="ranking")
        except repo.prompt_results.PromptResultExistsError as e:
            return JsonResponse({"status": "error", "error": str(e)}, status=400)
        except Exception as e:
            return JsonResponse({"status": "error", "error": str(e)}, status=400)

        return JsonResponse({"status": "success"}, status=200)

    def run(self, request):
        prompt_value = request.POST.get("prompt-value")
        story_limit = int(request.POST.get("story-limit"))
        is_vector_search = request.POST.get("is-vector-search")
        vector_query = request.POST.get("vector-query")
        sampling_method = request.POST.get("sampling-method")
        logger.info(f"Run Ranking|Vector Query: {vector_query}|Prompt: {prompt_value}")
        start_date = (
            datetime.datetime.now()
            - datetime.timedelta(days=int(request.POST.get("start-date")))
        ).isoformat()
        selected_attributes = [
            request.POST[key] for key in request.POST if key.startswith("attribute-")
        ]

        now = datetime.datetime.now().time()
        for start_time, end_time in constants.REPLICATION_PERIODS:
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
            return HttpResponse(f"<p>{e}</p><p>Please try again.</p>")

        llm_stories = services.sampling.sample_stories(
            stories=stories, limit=story_limit, sampling_method=sampling_method
        )
        data = services.make_concurrent_llm_requests_for_stories(
            stories=llm_stories, prompt=prompt_value, attributes=selected_attributes
        )
        html = render_to_string(
            "rank/output.html",
            {"llm_stories": data, "vector_stories": stories},
        )
        return HttpResponse(html)

    def output(self, request):
        story_ids = request.POST.getlist("story-id")
        vector_positions = request.POST.getlist("vector-position")
        similarity_scores = request.POST.getlist("similarity-score")
        prompt_value = request.POST.get("prompt-value")
        selected_attributes = [
            request.POST[key] for key in request.POST if key.startswith("attribute-")
        ]

        now = datetime.datetime.now().time()
        for start_time, end_time in constants.REPLICATION_PERIODS:
            if start_time <= now <= end_time:
                return HttpResponse(constants.REPLICATING_HTML_MSG)

        stories = [
            {
                "id": story_id,
                "vector_position": int(vector_position),
                "similarity_score": float(similarity_score),
            }
            for story_id, vector_position, similarity_score in zip(
                story_ids, vector_positions, similarity_scores
            )
        ]

        stories = sorted(
            repo.stories.get_repeat_stories(stories=stories), key=lambda x: x.position
        )
        data = services.make_concurrent_llm_requests_for_stories(
            stories=stories, prompt=prompt_value, attributes=selected_attributes
        )
        html = render_to_string(
            "rank/output.html",
            {"llm_stories": data, "vector_stories": stories},
        )
        return HttpResponse(html)

    def rerun(self, request):
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
            "rank/output.html",
            {"llm_stories": data, "vector_stories": stories},
        )
        return HttpResponse(html)
