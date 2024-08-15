from django.http import HttpResponse
from django.middleware.csrf import get_token


def get_csrf_token(request):
    return HttpResponse(get_token(request))
