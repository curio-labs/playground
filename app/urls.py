from django.urls import path

from . import utility_views as uv
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("score-ranking/", views.score_ranking, name="score_ranking"),
    path(
        "score-ranking-prompt/", views.score_ranking_prompt, name="score_ranking_prompt"
    ),
    path("rerank-stories/", views.rerank_stories, name="rerank_stories"),
    path("utility/get-csrf-token/", uv.get_csrf_token, name="get_csrf_token"),
    path("api/stories/<str:story_id>/", views.get_story_by_id, name="get_story_by_id"),
    path("api/scripts/<str:story_id>/", views.get_script, name="get_script"),
]
