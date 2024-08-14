from django.urls import path

from . import utility_views as uv
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("my-view/", views.my_view, name="my_view"),
    path("prompt/", views.prompt, name="prompt"),
    path("load-stories/", views.load_stories, name="load_stories"),
    path("utility/get-csrf-token/", uv.get_csrf_token, name="get_csrf_token"),
    path("add/", views.add_task, name="add"),
    path(
        "check_task_status/<str:task_id>/",
        views.check_task_status,
        name="check_task_status",
    ),
]
