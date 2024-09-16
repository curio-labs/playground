import logging

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from app import repo
from src import services

from .action import ActionView

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class TransformView(View, ActionView):
    template_name = "transform/index.html"

    def get(self, request):
        prompts = repo.prompt_results.get_all()
        return render(request, "transform/index.html", {"prompts": prompts})

    def post(self, request, action):
        if action == "save":
            return self.save(request)
        elif action == "run":
            return self.run(request)
        elif action == "prompts":
            return self.prompts(request)
        else:
            return JsonResponse({"error": "Invalid action"}, status=400)

    def prompts(self, request):
        prompt_id = request.POST.get("saved-prompts")
        results = repo.prompt_results.get_stories_by_prompt_id(prompt_id=prompt_id)
        if results["type"] == "ranking":
            html = render_to_string(
                "transform/select_stories.html", {"stories": results["data"]}
            )
        elif results["type"] == "news":
            print(results["data"][0])
            html = render_to_string(
                "transform/select_news_stories.html", {"stories": results["data"]}
            )
        else:
            raise ValueError(f"Invalid prompt type '{results['type']}'")
        return HttpResponse(html)

    def run(self, request):
        stories = request.POST.getlist("story-option")
        prompt = request.POST.get("prompt-value")
        results = services.get_stories_by_id(story_ids=stories)["data"]
        transformation = services.llm.transform_stories(stories=results, prompt=prompt)
        html = render_to_string(
            "transform/output.html",
            {"stories": results, "transformation": transformation},
        )
        return HttpResponse(html)
