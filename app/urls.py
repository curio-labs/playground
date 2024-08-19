from django.urls import path

from . import utility_views as uv
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("simple-ranking/", views.simple_ranking, name="simple_ranking"),
    path("score-ranking/", views.score_ranking, name="score_ranking"),
    path(
        "simple-ranking-prompt/",
        views.simple_ranking_prompt,
        name="simple_ranking_prompt",
    ),
    path(
        "score-ranking-prompt/", views.score_ranking_prompt, name="score_ranking_prompt"
    ),
    path("load-stories/", views.load_stories, name="load_stories"),
    path("utility/get-csrf-token/", uv.get_csrf_token, name="get_csrf_token"),
    path("api/stories/<str:story_id>/", views.get_story_by_id, name="get_story_by_id"),
    path("api/scripts/<str:story_id>/", views.get_script, name="get_script"),
    path("add/", views.add_task, name="add"),
    path(
        "check_task_status/<str:task_id>/",
        views.check_task_status,
        name="check_task_status",
    ),
]
