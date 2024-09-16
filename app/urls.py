from django.urls import path

from app.views import index as index_views
from app.views import news as news_views
from app.views import rank as rank_views
from app.views import stories as story_views
from app.views import transform as transform_views

from . import utility_views as uv

urlpatterns = [
    path("", index_views.index, name="index"),
    path("rank/", rank_views.RankingView.as_view(), name="rank"),
    path("rank/<str:action>/", rank_views.RankingView.as_view(), name="rank-action"),
    path("news/", news_views.NewsView.as_view(), name="news"),
    path("news/<str:action>/", news_views.NewsView.as_view(), name="news-action"),
    path("transform/", transform_views.TransformView.as_view(), name="transform"),
    path(
        "transform/<str:action>/",
        transform_views.TransformView.as_view(),
        name="transform-action",
    ),
    path("utility/get-csrf-token/", uv.get_csrf_token, name="get_csrf_token"),
    path(
        "api/stories/<str:story_id>/",
        story_views.get_story_by_id,
        name="get_story_by_id",
    ),
    path("api/scripts/<str:story_id>/", story_views.get_script, name="get_script"),
    path("api/scripts/<str:story_id>/", story_views.get_script, name="get_script"),
]
