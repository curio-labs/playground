from django.http import HttpResponse
from django.urls import path


def index(request):
    return HttpResponse("Hello, world. You're at the playground index.")


urlpatterns = [
    path("", index, name="index"),
]
