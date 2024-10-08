import json
import logging

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from app import repo
from src import services
from src.services.headlines import HeadlineStoryQueryStrategy

from .action import ActionView

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class NewsView(View, ActionView):
    template_name = "news/index.html"

    def get(self, request):
        return render(request, self.template_name)

    def save(self, request):
        prompt_name = request.POST.get("prompt-name")
        if not prompt_name:
            return JsonResponse(
                {"status": "error", "error": "Prompt name is required."}, status=400
            )

        news_market = request.POST.get("news-market")
        selected_news_feed = request.POST.get("selected-news-feed")
        headline_limit = request.POST.get("headline-limit")
        internal_story_matching = request.POST.get("internal-story-matching")
        prompt_value = request.POST.get("prompt-value")

        headlines = request.POST.get("headlines")
        if not headlines:
            return JsonResponse(
                {"status": "error", "error": "No stories selected."}, status=400
            )

        context = cache.get("cached_context")

        results = {
            "prompt_name": prompt_name,
            "news_market": news_market,
            "selected_news_feed": selected_news_feed,
            "headline_limit": headline_limit,
            "internal_story_matching": internal_story_matching,
            "prompt_value": prompt_value,
            "context": context,
        }

        try:
            repo.prompt_results.save(results=results, playground="news")
            return JsonResponse({"status": "success", "results": results})
        except repo.prompt_results.PromptResultExistsError as e:
            return JsonResponse({"status": "error", "error": str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            return JsonResponse({"status": "error", "error": str(e)}, status=400)

    def run(self, request):
        prompt_value = request.POST.get("prompt-value")
        news_market = request.POST.get("news-market")
        selected_news_feed = request.POST.get("selected-news-feed")
        headline_limit = int(request.POST.get("headline-limit"))
        is_top_headlines = selected_news_feed == "top-headlines"
        story_matching_strategy = request.POST.get("internal-story-matching")
        dedupe_headlines = request.POST.get("dedupe-headlines")
        dedupe_headlines = dedupe_headlines == "true"
        dedupe_thresh = float(request.POST.get("dedupe-threshold"))

        logger.info(f"News Ranking | Market: {news_market} | Prompt: {prompt_value}")

        try:
            raw_headlines = services.headlines.get_all_bing_news_headlines(
                market=news_market,
                use_top_headlines_feed=is_top_headlines,
                headline_limit=headline_limit,
            )
            if dedupe_headlines:
                headlines = services.headlines.dedupe_headlines(
                    raw_headlines, dedupe_thresh
                )
            else:
                headlines = raw_headlines

        except ValueError as e:
            return HttpResponse(f"<p>{e}</p><p>Please try again.</p>")

        reranked_headlines = (
            services.llm.make_concurrent_llm_request_for_headline_scoring(
                headlines=headlines, relevancy_prompt=prompt_value
            )
        )

        scored_story_matches = None
        if story_matching_strategy:
            strategy = HeadlineStoryQueryStrategy.from_user_str(story_matching_strategy)
            scored_story_matches = (
                services.headlines.match_headlines_to_internal_stories(
                    [headline for headline, _ in reranked_headlines], strategy
                )
            )

        context = {
            "headlines": raw_headlines,
            "reranked_headlines": reranked_headlines,
            "reranked_headlines_and_stories": list(
                zip(reranked_headlines, scored_story_matches)
            )
            if scored_story_matches
            else None,
            "has_story_matches": bool(scored_story_matches),
        }
        headlines = [h.dict() for h in headlines]
        reranked_headlines = [
            {**h.dict(), "score": score} for h, score in reranked_headlines
        ]
        scored_story_matches = (
            [{**s[0], "match_score": s[1]} for s in scored_story_matches]
            if scored_story_matches
            else None
        )
        reranked_headlines_and_stories = (
            list(zip(reranked_headlines, scored_story_matches))
            if scored_story_matches
            else None
        )
        has_story_matches = bool(scored_story_matches)

        json_context = {
            "headlines": headlines,
            "reranked_headlines": reranked_headlines,
            "reranked_headlines_and_stories": reranked_headlines_and_stories,
            "has_story_matches": has_story_matches,
        }
        cache.set("cached_context", json_context, timeout=None)

        html = render_to_string("news/output.html", context)
        return HttpResponse(html)
